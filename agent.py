import os
import sys

from dotenv import load_dotenv
from google import genai
from google.genai import errors, types

load_dotenv()

MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")

SUPPORTED_TYPES = {
    ".pdf":"application/pdf",
    ".txt":"text/plain",
    ".md":"text/markdown",
    ".csv":"text/csv",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}

INSTRUCTIONS = """
Bạn là trợ lý phân tích tài liệu.

Quy tắc:
1. Dùng file người dùng cung cấp làm nguồn thông tin chính.
2. Trả lời thẳng vào câu hỏi.
3. Không bịa ra thông tin mà file không có.  
4. Không bịa ra thông tin để trả lời, hãy nói rõ.
5. Khi tóm tắt ưu tiên những ý quan trọng nhấ.
6. Với bài nghiên cứu, tách bạch phương phá, kết quả và kết luận.
7. Với dữ liệu dạng bảng, chỉ nêu số liệu có trong file, không tự tính ra số mới nếu không được yêu cầu.
8. Nếu đưa ra suy luận, ghi rõ đó là suy luận.
9. Dùng ngôn ngữ dễ hiểu; dùng gạch đầu dòng khi giúp câu trả lời rõ hơn.
10. Luôn trả lời bằng tiếng Việt, giữ nguyên thuật ngữ chuyên ngành khi cần.                                     
"""

def read_file_path():
    return input("Enter the path to your file: ").strip().strip('"').strip("'")

def upload_file(client, file_path, mime_type):
    with open(file_path, "rb") as f:
        return client.files.upload(
            file=f,
            config=types.UploadFileConfig(
                mime_type=mime_type,
                display_name=os.path.basename(file_path),
            ),
        )


def explain_api_error(error):
    if error.code == 429:
        return "Đã chạm hạn mức (quota) của project. Đợi một lúc rồi thử lại."
    if error.code in (400, 401, 403) and "key" in str(error.message).lower():
        return "API key không hợp lệ hoặc không có quyền. Kiểm tra lại file .env"
    if error.code == 404:
        return f"Không tìm thấy model {MODEL}. Hãy kiểm tra lại tên model."

def main():
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        sys.exit("Chưa có GEMINI_API_KEY. Hãy khai báo trong file .env")

    file_path = read_file_path()
    if not os.path.isfile(file_path):
        sys.exit(f"Không tìm thấy file: {file_path}")

    extension = os.path.splitext(file_path)[1].lower()
    mime_type = SUPPORTED_TYPES.get(extension)
    if mime_type is None:
        sys.exit(f"Chưa hỗ trợ đuôi '{extension}'. Các đuôi hỗ trợ được {', '.join(SUPPORTED_TYPES.keys())}.")

    client = genai.Client(api_key=api_key)
    try:
        uploaded_file = upload_file(client, file_path, mime_type)
    except errors.APIError as error:
        sys.exit("Upload thất bại. " + str(explain_api_error(error)))
    except Exception as error:
        sys.exit(f"Upload thất bại: {error}")

    print(f"Đã Upload: {uploaded_file.display_name}")

    chat = client.chats.create(
        model=MODEL,
        config=types.GenerateContentConfig(system_instruction=INSTRUCTIONS),
    )

    try:
        while True:
            question = input("\nYou: ").strip()
            if question.lower == exit:
                break
            if not question:
                print("Hãy nhập câu hỏi.")
                continue

            if chat.get_history(curated =True):
                message = question
            else:
                message = [uploaded_file, question]

            try:
                response = chat.send_message(message)
            except errors.APIError as error:
                print("\n" + str(explain_api_error(error)))
            except Exception as error:
                print(f"Lỗi kết nối hoặc lỗi không mong đợi: {error}")
                continue

            print("\nAgent:")
            print(response.text or "Không nhận được nội dung câu trả lời")
    except (KeyboardInterrupt, EOFError):
        print()
    finally:
        try:
            client.files.delete(name=uploaded_file.display_name)
            print("Đã xóa file khỏi máy chủ Gemini. Tạm biệt!")
        except Exception:
            print("Không xóa được file trên máy chủ Gemini; Gemini sẽ tự xóa sau 48h")

if __name__ == "__main__":
    main()