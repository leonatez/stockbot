import os
from dotenv import load_dotenv
import json
from google import genai
load_dotenv() 

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=GEMINI_API_KEY)
model = "gemini-2.5-pro"

def analyze_with_gemini(all_posts_content: str) -> list[dict]:
    """Analyze collected posts using Gemini to extract stock information"""
    if not model or not all_posts_content.strip():
        print("Gemini model not available or no content to analyze")
        return []
    
    try:
        prompt = f"""
        You are stock investment consultant in Vietnam. 
        Analyze the following financial news content about Vietnamese companies 
        and extract information about stocks mentioned. 
        Keep in mind that all those stocks are Vietnamese stocks just to 
        distinguish with foreign stocks having the same symbol.
        For each stock symbol found, provide the analysis in this exact JSON format:

        {{
            "stock_symbol": "SYMBOL",
            "mentioned_times": number,
            "sentiment": "positive/negative/neutral",
            "summary": "Brief summary of how this stock was mentioned and what news affects it"
        }}

        Rules:
        1. Only include actual stock symbols (like HPG, ACB, LDG, etc.)
        2. Count how many posts each symbol is mentioned across all posts
        3. Determine if the overall sentiment is positive, negative, or neutral
        4. Provide a concise summary of the key points about each stock
        5. Return ONLY a valid JSON array, no other text
        6. If no stocks are found, return an empty array []

        Content to analyze:
        {all_posts_content}
        """
        
        print("Sending content to Gemini for analysis...")
        response = client.models.generate_content(model=model, contents=prompt)
        
        if response and response.text:
            # Clean the response text
            response_text = response.text.replace("```json", "").replace("```", "").strip()
            print(f"Received response from Gemini: {response.text}")
            # Try to extract JSON from the response
            try:
                # Look for JSON array in the response
                start_idx = response_text.find('[')
                end_idx = response_text.rfind(']') + 1
                
                if start_idx != -1 and end_idx != -1:
                    json_str = response_text[start_idx:end_idx]
                    stocks_data = json.loads(json_str)
                    
                    print(f"Successfully parsed {len(stocks_data)} stock analyses from Gemini")
                    return stocks_data
                else:
                    print("No JSON array found in Gemini response")
                    return []
                    
            except json.JSONDecodeError as e:
                print(f"Failed to parse JSON from Gemini response: {e}")
                print(f"Raw response: {response_text[:500]}...")
                return []
        else:
            print("No valid response from Gemini")
            return []
            
    except Exception as e:
        print(f"Error calling Gemini API: {e}")
        return []

all_posts_content = """
QTP công bố kết quả kinh doanh (KQKD) Q2/2025 với doanh thu đạt 2.912 tỷ đồng, -21,1% svck, lợi nhuận gộp đạt 267 tỷ đồng, +26,5% svck, và LNST đạt 190 tỷ đồng, +18,0% svck, hoàn thành 79% kế hoạch và 82% dự phóng của ACBS cho năm 2025. LNST tăng trưởng chủ yếu do chi phí đầu vào giảm mạnh trong Q2/2025 (-25,3% svck), bù đắp cho sự sụt giảm của sản lượng (-1,9% svck) và giá bán (-19,5% svck). Chúng tôi đưa ra khuyến nghị Khả Quan cho QTP với giá mục tiêu 14.600 đồng/cp, ứng với tổng tỷ suất sinh lời kỳ vọng 18,3%.

Sản lượng điện Q2/2025 đạt gần 2,0 tỷ kWh, -1,9% svck, doanh thu giảm 21,1% svck, do ảnh hưởng cộng hưởng từ giá bán bình quân giảm 19,5% svck, đạt bình quân 1.442 đồng/kWh. Nguyên nhân do ảnh hưởng chung từ giá bán điện toàn phần (FMP) sụt giảm trên thị trường cạnh tranh. Cụ thể, giá FMP Q2/2025 bình quân đạt 1.317 đồng/kWh, -9,0% svck. Tuy nhiên, lãi gộp tăng 26,5% svck, lên 267 tỷ đồng và biên lãi gộp cải thiện từ 5,8% cùng kỳ lên 9,3%, nhờ tiết giảm được nhiều chi phí, chủ yếu là chi phí nguyên liệu đầu vào (than) giảm mạnh. Cụ thể, chi phí nguyên liệu ghi nhận 2.248 tỷ đồng, -25,3% svck. Nhờ đó, LNST đạt 190 tỷ đồng, +18,0% svck, biên lãi ròng cải thiện lên 6,6% từ 4,4% cùng kỳ. Lũy kế 6T2025, sản lượng đạt gần 3,8 tỷ kWh, -1,0% svck, doanh thu đạt 6.638 tỷ đồng, -13,0% svck, LNST đạt 388 tỷ đồng, -6,4% svck, biên lãi ròng cải thiện từ 5,8% cùng kỳ lên 6,3%.

"""
print(analyze_with_gemini(all_posts_content))

# test = """
# ```json
# [
#     {
#         "stock_symbol": "QTP",
#         "mentioned_times": 2,
#         "sentiment": "positive",
#         "summary": "QTP announced Q2/2025 business results with net profit after tax reaching 190 billion VND, an increase of 18.0% over the same period last year. This growth was mainly due to a sharp decrease in input costs, which offset the decline in revenue and sales volume. The company received a 'Positive' (Khả Quan) recommendation with a target price of 14,600 VND/share."
#     }
# ]
# ```
# """

# response_text = test.replace("```json", "").replace("```", "").strip()
# print(response_text)
# start_idx = response_text.find('[')
# end_idx = response_text.rfind(']') + 1
# if start_idx != -1 and end_idx != -1:
#     json_str = response_text[start_idx:end_idx]
#     stocks_data = json.loads(json_str)
#     print(f"Successfully parsed {len(stocks_data)} stock analyses from Gemini")

# else:
#     print("No JSON array found in Gemini response")



