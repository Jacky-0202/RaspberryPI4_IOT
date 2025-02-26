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
| **N01** | Entering network parameter input phase         |
| **N02** | No SSID or password recorded                   |
| **N03** | Enabling network priority                      |
| **N04** | Automatically searching for available networks |
| **N05** | Network detected, but signal is unstable       |
| **N06** | Network connection successful                  |
| **N07** | Incorrect SSID or password entered             |
| **N08** | Reading network signal strength                |
| **N09** | Successfully uploaded compressed file          |
| **N10** | Upload function disabled                       |
|         |                                                |
| ===     | ===                                            |
| **C01** | Camera started successfully                    |
| **C02** | Using saved camera focus distance parameter    |
| **C03** | Saving camera focus distance parameter         |
| **C04** | Using saved white balance parameters           |
| **C05** | Saving white balance parameters                |
| **C06** | Auto exposure adjustment completed             |
| **C07** | Image successfully saved                       |
| **C08** | Camera closed                                  |
| **C09** | Failed to get AWB gains.                       |
|         |                                                |
| ===     | ===                                            |
| **D01** | Configuration file saved                       |
| **D02** | Compressing files for upload (.zip)            |
|         |                                                |
| ===     | ===                                            |
| **S01** | Successfully recorded sensor data              |
| **S02** | Successfully uploaded sensor data              |
| **S03** | Sensor function disabled                       |


> PSWD : 對應網路的 password 縮寫

- error log

| 編號   | 訊息                                |
| ---- | --------------------------------- |
| N100 | Unable to connect to the Internet |
|      |                                   |
