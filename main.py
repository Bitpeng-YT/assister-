import base58
import json
import time
from datetime import datetime
import requests
import nacl.signing
from solders.keypair import Keypair
from colorama import init, Fore, Style
import os
from typing import Dict, List, Optional
import logging

# 初始化colorama
init()

# 配置文件路径
ACCOUNTS_PATH = 'accounts.txt'
PROXY_PATH = 'proxies.txt'

class AssisterClaimer:
    def __init__(self):
        self.base_url = "https://api.assisterr.ai/incentive"
        self.headers = {
            'accept': 'application/json',
            'origin': 'https://build.assisterr.ai',
            'referer': 'https://build.assisterr.ai/',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }

    def log(self, pubkey: str, message: str, msg_type: str = 'info') -> None:
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        colors = {
            'success': Fore.GREEN,
            'error': Fore.RED,
            'warning': Fore.YELLOW,
            'system': Fore.CYAN,
            'info': Fore.MAGENTA
        }
        color = colors.get(msg_type, Fore.WHITE)
        
        if msg_type == 'system':
            print(f"{Fore.WHITE}[{Fore.LIGHTBLACK_EX}{timestamp}{Fore.WHITE}] {color}{message}{Style.RESET_ALL}")
        else:
            if message.startswith('处理中') and pubkey and pubkey != 'UNKNOWN':
                print(f"{Fore.WHITE}[{Fore.LIGHTBLACK_EX}{timestamp}{Fore.WHITE}] {color}处理中 {Fore.YELLOW}{pubkey}{Style.RESET_ALL}")
            else:
                print(f"{Fore.WHITE}[{Fore.LIGHTBLACK_EX}{timestamp}{Fore.WHITE}] {color}{message}{Style.RESET_ALL}")

    def read_accounts(self) -> List[Dict]:
        try:
            with open(ACCOUNTS_PATH, 'r', encoding='utf-8') as f:
                lines = f.read().splitlines()
            return [
                dict(zip(['token', 'refreshToken', 'privateKey'], line.split(':')))
                for line in lines if line.strip()
            ]
        except Exception as e:
            self.log('系统', f"读取账户时出错: {str(e)}", 'error')
            return []

    def read_proxies(self) -> List[str]:
        try:
            with open(PROXY_PATH, 'r', encoding='utf-8') as f:
                return [line.strip() for line in f if line.strip()]
        except:
            return []

    def update_account_file(self, accounts: List[Dict]) -> None:
        content = '\n'.join(f"{acc['token']}:{acc['refreshToken']}:{acc['privateKey']}" 
                          for acc in accounts)
        with open(ACCOUNTS_PATH, 'w', encoding='utf-8') as f:
            f.write(content)

    def get_public_key(self, private_key: str) -> str:
        if not private_key:
            return 'UNKNOWN'
        try:
            secret_key = base58.b58decode(private_key.strip())
            # 使用nacl.signing来处理密钥对
            signing_key = nacl.signing.SigningKey(secret_key)
            verify_key = signing_key.verify_key
            public_key_bytes = verify_key.encode()
            return base58.b58encode(public_key_bytes).decode()
        except Exception as e:
            # 不打印错误信息，静默处理
            return 'UNKNOWN'

    def make_request(self, method: str, endpoint: str, proxy: Optional[str] = None, 
                    **kwargs) -> requests.Response:
        url = f"{self.base_url}/{endpoint.lstrip('/')}"
        if proxy:
            kwargs['proxies'] = {'http': proxy, 'https': proxy}
        kwargs['headers'] = {**self.headers, **kwargs.get('headers', {})}
        return requests.request(method, url, **kwargs)

    async def process_account(self, account: Dict, proxy: Optional[str] = None) -> Dict:
        public_key = self.get_public_key(account['privateKey'])
        try:
            current_account = account.copy()
            self.log(public_key, '处理中', 'info')

            # 检查用户状态
            resp = self.make_request('GET', '/users/me/', proxy,
                                   headers={'authorization': f"Bearer {current_account['token']}"})
            user_status = resp.json()

            if not user_status.get('id'):
                self.log('', '令牌已过期，尝试刷新...', 'info')
                # 刷新令牌
                resp = self.make_request('POST', '/auth/refresh_token/', proxy,
                                       headers={'authorization': f"Bearer {current_account['refreshToken']}"})
                refresh_result = resp.json()

                if refresh_result.get('access_token'):
                    current_account['token'] = refresh_result['access_token']
                    current_account['refreshToken'] = refresh_result['refresh_token']
                    self.log('', '令牌刷新成功', 'success')
                else:
                    self.log('', '令牌刷新失败，尝试新登录...', 'warning')
                    # 获取登录消息
                    resp = self.make_request('GET', '/auth/login/get_message/', proxy)
                    message = resp.text.strip('"')

                    # 签名消息
                    secret_key = base58.b58decode(current_account['privateKey'])
                    keypair = Keypair.from_secret_key(secret_key)
                    signer = nacl.signing.SigningKey(secret_key)
                    signature = base58.b58encode(signer.sign(message.encode()).signature).decode()

                    # 登录
                    resp = self.make_request('POST', '/auth/login/', proxy,
                                           json={'message': message,
                                                'signature': signature,
                                                'key': str(keypair.public_key)})
                    login_result = resp.json()

                    if not login_result.get('access_token'):
                        raise Exception('登录失败')
                    current_account['token'] = login_result['access_token']
                    current_account['refreshToken'] = login_result['refresh_token']
                    self.log('', '新登录成功', 'success')

            # 获取用户元数据
            resp = self.make_request('GET', '/users/me/meta/', proxy,
                                   headers={'authorization': f"Bearer {current_account['token']}"})
            meta = resp.json()

            if meta.get('daily_points_start_at'):
                next_claim = datetime.fromisoformat(meta['daily_points_start_at'].replace('Z', '+00:00'))
                if next_claim > datetime.now():
                    time_until = int((next_claim - datetime.now()).total_seconds() / 60)
                    self.log('', f"下次领取在 {time_until} 分钟后可用", 'info')
                    return current_account

            # 领取每日奖励
            resp = self.make_request('POST', '/users/me/daily_points/', proxy,
                                   headers={'authorization': f"Bearer {current_account['token']}"})
            claim_result = resp.json()

            if claim_result.get('points'):
                self.log('', f"领取成功！获得 {claim_result['points']} 点", 'success')
                next_claim_time = datetime.fromisoformat(
                    claim_result['daily_points_start_at'].replace('Z', '+00:00'))
                self.log('', f"下次领取时间: {next_claim_time.strftime('%Y-%m-%d %H:%M:%S')}", 'info')
            else:
                self.log('', f"领取失败: {json.dumps(claim_result)}", 'error')

            return current_account
        except Exception as e:
            self.log('', f"错误: {str(e)}", 'error')
            return account

    def print_banner(self):
        banner = '''
               ╔═╗─╔╗╔══╗╔═╗─╔╗╔═══╗╔═══╗
               ║║╚╗║║║╔╗║║║╚╗║║║╔═╗║║╔═╗║
               ║╔╗╚╝║║║║║║╔╗╚╝║║║─║║║║─║║
               ║║╚╗║║║║║║║║╚╗║║║╔═╝║║║─║║
               ║║─║║║║╚╝║║║─║║║║║╔═╗║╚═╝║
               ╚╝─╚═╝╚══╝╚╝─╚═╝╚╝╚═╝╚═══╝
               
               Assister自动签到程序
               作者Github: github.com/Bitpeng-YT
               作者推特: 纸盒忍者@Web3CartonNinja                  
        '''
        print(Fore.CYAN + banner + Style.RESET_ALL)

    async def main(self):
        os.system('cls' if os.name == 'nt' else 'clear')
        self.print_banner()
        print(Fore.CYAN + '每日自动领取已启动！\n' + Style.RESET_ALL)

        accounts = self.read_accounts()
        proxies = self.read_proxies()

        if proxies:
            print(Fore.YELLOW + f"已加载 {len(proxies)} 个代理" + Style.RESET_ALL)
        else:
            print(Fore.RED + '未找到代理，使用直接连接' + Style.RESET_ALL)

        print(Fore.MAGENTA + f"处理 {len(accounts)} 个账户\n" + Style.RESET_ALL)

        updated_accounts = []
        for i, account in enumerate(accounts):
            proxy = proxies[i % len(proxies)] if proxies else None
            updated_account = await self.process_account(account, proxy)
            updated_accounts.append(updated_account)

        self.update_account_file(updated_accounts)
        print('\n')
        self.log('系统', '所有账户已处理，等待下一个周期...', 'success')

if __name__ == "__main__":
    import asyncio
    
    claimer = AssisterClaimer()
    while True:
        asyncio.run(claimer.main())
        time.sleep(3600)  # 每小时运行一次 