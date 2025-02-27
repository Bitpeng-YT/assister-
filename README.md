# Assister 自动签到脚本 
每日自动签到 assister 获取积分

## 功能特点

- 自动每日签到领取积分
- 支持多账户管理
- 支持代理服务器
- 自动令牌刷新
- 自动重新登录
- 彩色日志输出
- 定时执行（每小时检查一次）

## 安装步骤

1. 确保已安装Python 3.7或更高版本
2. 安装依赖包：
   ```bash
   pip install -r requirements.txt
   ```

## 获取token
1. 获取你的 Solana 钱包私钥 privateKey
2. 获取账户API：
   - 打开 [https://build.assisterr.ai](https://build.assisterr.ai/?ref=6793523d0cdf4b440a3139d6)，确保你已登录。
   - 打开浏览器的开发者工具，按 F12 或 Ctrl+Shift+I，切换到控制台 Console。
   - 运行以下命令：
   ```bash
   (() => {
    // 清除控制台
    console.clear();
    
    // 设置输出样式
    const styles = {
        title: 'color: #2196F3; font-size: 14px; font-weight: bold;',
        success: 'color: #4CAF50; font-size: 13px;',
        error: 'color: #F44336; font-size: 13px;',
        info: 'color: #9E9E9E; font-size: 12px;'
    };

    console.log('%c=== Assister Token 获取工具 ===', styles.title);
    console.log('%c提示：请确保您已经登录 Assister', styles.info);

    // 获取并显示tokens
    const tokens = document.cookie
        .split(';')
        .reduce((acc, cookie) => {
            const [name, value] = cookie.trim().split('=');
            if (name === 'accessToken') {
                console.log('%caccessToken:', styles.success, decodeURIComponent(value));
                acc.accessToken = decodeURIComponent(value);
            }
            if (name === 'refreshToken') {
                console.log('%crefreshToken:', styles.success, decodeURIComponent(value));
                acc.refreshToken = decodeURIComponent(value);
            }
            return acc;
        }, {});

    if (!tokens.accessToken || !tokens.refreshToken) {
        console.log('%c未找到Token，请确保已经登录网站', styles.error);
    }
   })();
   ```

## 账户配置方法

1. 创建 `accounts.txt` 文件，每行包含一个账户信息，格式为：
   ```
   accessToken:refreshToken:privateKey
   ```

2. 创建 `proxies.txt` 文件，每行一个代理地址，格式为：
   ```
   http://user:pass@host:port
   ```
   或
   ```
   http://host:port
   ```

3. 运行脚本：
   ```bash
   python main.py
   ```

## 注意事项

- 请妥善保管您的私钥和令牌信息
- 建议使用代理服务器以避免IP限制
- 脚本会自动处理令牌过期和刷新
- 如果遇到问题，请查看控制台输出的错误信息

## 免责声明

本脚本仅供学习和研究使用，使用本脚本所产生的任何女巫后果由使用者自行承担。
