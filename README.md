main.py : Tool

generate-raw-table.py : Tạo nhãn thô sử dụng FasterRCNN, output ra thằng file json dùng cho tool, link mô hình: https://drive.google.com/file/d/1hmuk3ouPDpu1sw8ioOsPw7bQxhEKykh5/view?usp=sharing

convert-jsonl.py : Tạo file jsonl từ folder nhãn

OCR.py : detect text box dùng paddleOCR, output chỉ lưu box, lưu txt

convert-box.py: kết hợp box từ tool + text box từ OCR để tạo 3 dạng box mới (loại box rỗng, loại box rỗng + bo sát vào content, loại box rỗng + bo vào một chút)
