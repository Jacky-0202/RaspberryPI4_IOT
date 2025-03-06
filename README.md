---
tags:
  - Python
  - Erorr_Log
  - Raspberry_Pi
create: 2025-02-24
update: 2025-02-24
---
### 摘要

在 Raspberry Pi 上實作感測器收集資料、拍照、壓縮上傳到 Server 端後，需要
1. 軟體環境建立
2. 資料的分類 (廠商、照片、感測器資訊、Log...)
3. 影像處理、資料處裡
4. 資料儲存方式 (MySQL)
5. LineBot 管理
6. 網頁管理

---
### log 紀錄

- messege log

| Code    | Message                                        |
| ------- | ---------------------------------------------- |
| **M00** | Entering network parameter input phase         |
| **M00** | No SSID or password recorded                   |
| **M00** | Enabling network priority                      |
| **M00** | Automatically searching for available networks |
| **M00** | Network detected, but signal is unstable       |
| **M00** | Network connection successful                  |
| **M00** | Incorrect SSID or password entered             |
| **M00** | Reading network signal strength                |
| **M00** | Successfully uploaded compressed file          |
| **M00** | Upload function disabled                       |
|         |                                                |
| ===     | ===                                            |
| **M00** | Camera started successfully                    |
| **M00** | Using saved camera focus distance parameter    |
| **M00** | Saving camera focus distance parameter         |
| **M00** | Using saved white balance parameters           |
| **M00** | Saving white balance parameters                |
| **M00** | Auto exposure adjustment completed             |
| **M00** | Image successfully saved                       |
| **M00** | Camera closed                                  |
| **M00** | Failed to get AWB gains.                       |
|         |                                                |
| ===     | ===                                            |
| **M00** | Configuration file saved                       |
| **M00** | Compressing files for upload (.zip)            |
|         |                                                |
| ===     | ===                                            |
| **M00** | Successfully recorded sensor data              |
| **M00** | Successfully uploaded sensor data              |
| **M00** | Sensor function disabled                       |


> PSWD : 對應網路的 password 縮寫

- error log

| Code    | Message                           |
| ------- | --------------------------------- |
| **E00** | Unable to connect to the Internet |
