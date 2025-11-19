import json
import os
import re
from datetime import datetime
from playwright.sync_api import sync_playwright
import requests


def get_current_price():
    """웹사이트에서 현재 가격을 가져옵니다."""
    url = "https://www.truerewards.co.nz/merchandise/Technology/TC7493"
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            
            # 페이지 로드
            page.goto(url, timeout=30000)
            
            # JavaScript가 로드될 때까지 대기
            page.wait_for_timeout(5000)
            
            # 정확한 가격 선택자로 가격 찾기
            price_selector = '#content > section > div.tr-fixed-container.product-detail > div:nth-child(2) > div.col-md-10.col-lg-25.col-md-no-padding > div > div > div > div.aciem-not-special-or-deal.yellow-text > span > span'
            
            try:
                # 가격 요소가 나타날 때까지 대기
                page.wait_for_selector(price_selector, timeout=10000)
                
                # 가격 텍스트 가져오기
                price_element = page.query_selector(price_selector)
                if price_element:
                    price_text = price_element.inner_text().strip()
                    print(f"Found price text: {price_text}")
                    
                    # 숫자만 추출 (TR$, $, 쉼표 제거)
                    price_text = price_text.replace('TR$', '').replace('$', '').replace(',', '').strip()
                    
                    try:
                        price = float(price_text)
                        print(f"Extracted price: ${price:.2f}")
                        browser.close()
                        return price
                    except ValueError:
                        print(f"Could not convert '{price_text}' to float")
            
            except Exception as e:
                print(f"Price element not found: {e}")
            
            # 스크린샷 저장 (디버깅용)
            page.screenshot(path='page_screenshot.png', full_page=True)
            print("Could not find price")
            
            browser.close()
            return None
            
    except Exception as e:
        print(f"Error fetching price: {e}")
        import traceback
        traceback.print_exc()
        return None


def load_previous_price():
    """이전에 저장된 가격을 불러옵니다."""
    try:
        with open('price_history.json', 'r') as f:
            data = json.load(f)
            return data.get('price')
    except FileNotFoundError:
        return 349.00  # 초기 가격


def save_price(price):
    """현재 가격을 파일에 저장합니다."""
    data = {
        'price': price,
        'last_checked': datetime.now().isoformat()
    }
    with open('price_history.json', 'w') as f:
        json.dump(data, f, indent=2)


def send_email(old_price, new_price):
    """SendGrid를 통해 가격 변동 이메일을 보냅니다."""
    api_key = os.environ.get('SENDGRID_API_KEY')
    if not api_key:
        print("SendGrid API key not found")
        return
    
    email_to = os.environ.get('EMAIL_TO')
    
    # 가격 변동 계산
    price_change = new_price - old_price
    change_percent = (price_change / old_price) * 100
    
    # 가격 상승/하락에 따른 이모지
    emoji = "📉" if price_change < 0 else "📈"
    
    data = {
        "personalizations": [{
            "to": [{"email": email_to}],
            "subject": f"{emoji} 가격 변동 알림 - True Rewards"
        }],
        "from": {"email": "noreply@github.com"},
        "content": [{
            "type": "text/html",
            "value": f"""
            <html>
            <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px; background-color: #f9f9f9;">
                    <h2 style="color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px;">
                        {emoji} 가격이 변경되었습니다!
                    </h2>
                    
                    <div style="background-color: white; padding: 20px; border-radius: 8px; margin: 20px 0;">
                        <h3 style="color: #34495e; margin-top: 0;">Apple AirPods 4 with Active Noise Cancellation</h3>
                        
                        <table style="width: 100%; border-collapse: collapse; margin: 15px 0;">
                            <tr>
                                <td style="padding: 10px; border-bottom: 1px solid #eee;"><strong>이전 가격:</strong></td>
                                <td style="padding: 10px; border-bottom: 1px solid #eee; text-align: right;">
                                    <span style="text-decoration: line-through; color: #95a5a6;">TR$ {old_price:.2f}</span>
                                </td>
                            </tr>
                            <tr>
                                <td style="padding: 10px; border-bottom: 1px solid #eee;"><strong>현재 가격:</strong></td>
                                <td style="padding: 10px; border-bottom: 1px solid #eee; text-align: right;">
                                    <span style="font-size: 24px; color: {'#27ae60' if price_change < 0 else '#e74c3c'}; font-weight: bold;">
                                        TR$ {new_price:.2f}
                                    </span>
                                </td>
                            </tr>
                            <tr>
                                <td style="padding: 10px;"><strong>변동:</strong></td>
                                <td style="padding: 10px; text-align: right;">
                                    <span style="color: {'#27ae60' if price_change < 0 else '#e74c3c'}; font-weight: bold;">
                                        {'▼' if price_change < 0 else '▲'} TR$ {abs(price_change):.2f} ({change_percent:+.1f}%)
                                    </span>
                                </td>
                            </tr>
                        </table>
                        
                        <div style="margin-top: 20px; text-align: center;">
                            <a href="https://www.truerewards.co.nz/merchandise/Technology/TC7493" 
                               style="display: inline-block; padding: 12px 30px; background-color: #3498db; color: white; 
                                      text-decoration: none; border-radius: 5px; font-weight: bold;">
                                제품 보러 가기 →
                            </a>
                        </div>
                    </div>
                    
                    <p style="font-size: 12px; color: #7f8c8d; text-align: center; margin-top: 20px;">
                        확인 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} UTC<br>
                        이 이메일은 GitHub Actions에 의해 자동으로 발송되었습니다.
                    </p>
                </div>
            </body>
            </html>
            """
        }]
    }
    
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Content-Type': 'application/json'
    }
    
    try:
        response = requests.post(
            'https://api.sendgrid.com/v3/mail/send',
            headers=headers,
            json=data
        )
        if response.status_code == 202:
            print("Email sent successfully")
        else:
            print(f"Failed to send email: {response.status_code}")
            print(f"Response: {response.text}")
    except Exception as e:
        print(f"Error sending email: {e}")


def main():
    """메인 실행 함수"""
    print("=" * 50)
    print(f"Price Check Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)
    
    # 현재 가격 가져오기
    current_price = get_current_price()
    
    if current_price is None:
        print("Could not fetch current price")
        exit(1)
    
    print(f"Current price: TR$ {current_price:.2f}")
    
    # 이전 가격 불러오기
    previous_price = load_previous_price()
    print(f"Previous price: TR$ {previous_price:.2f}")
    
    # 가격 변동 확인
    if current_price != previous_price:
        print("=" * 50)
        print("🔔 Price changed! Sending email...")
        print(f"Change: TR$ {previous_price:.2f} → TR$ {current_price:.2f}")
        print("=" * 50)
        send_email(previous_price, current_price)
        save_price(current_price)
    else:
        print("✓ Price unchanged")
        save_price(current_price)
    
    print("=" * 50)
    print("Price check completed successfully")
    print("=" * 50)


if __name__ == "__main__":
    main()
