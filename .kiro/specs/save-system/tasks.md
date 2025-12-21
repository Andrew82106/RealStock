# Implementation Plan: Save System (存档系统)

## Overview

本实现计划将存档系统分为后端服务、API路由、前端服务和UI组件四个主要部分，采用增量开发方式，确保每个步骤都可验证。

## Tasks

- [x] 1. 创建后端存档服务核心
  - [x] 1.1 创建 SaveService 类和数据模型
    - 创建 `api/services/save_service.py`
    - 定义 SaveMetadata、SaveData 数据类
    - 实现 storage 目录结构初始化
    - _Requirements: 7.1, 7.2_

  - [x] 1.2 编写 SaveService 属性测试
    - **Property 3: Save Creation Produces Valid File**
    - **Property 11: Filename Sanitization**
    - **Validates: Requirements 2.2, 7.1, 7.2, 7.3**

  - [x] 1.3 实现存档创建和验证功能
    - 实现 `create_save()` 方法
    - 实现 `sanitize_filename()` 方法
    - 实现 `validate_save_data()` 方法
    - _Requirements: 2.2, 2.3, 2.4, 7.3_

  - [x] 1.4 编写存档创建属性测试
    - **Property 4: Empty Name Rejection**
    - **Property 5: Duplicate Name Rejection**
    - **Property 6: New Save Has Empty Portfolio**
    - **Validates: Requirements 2.3, 2.4, 2.5**

  - [x] 1.5 实现存档读写功能
    - 实现 `load_save()` 方法
    - 实现 `update_save()` 方法
    - 实现 `list_saves()` 方法
    - 实现 `delete_save()` 方法
    - _Requirements: 1.1, 4.1, 6.2_

  - [x] 1.6 编写存档读写属性测试
    - **Property 1: Save-Load Round Trip**
    - **Property 2: Save List Completeness**
    - **Property 10: Save Deletion Removes File**
    - **Validates: Requirements 1.1, 1.2, 4.1, 4.2, 4.3, 4.4, 6.2, 6.3**

  - [x] 1.7 实现股票管理功能
    - 实现 `add_stock_to_save()` 方法
    - _Requirements: 3.1, 5.3_

  - [x] 1.8 编写股票管理属性测试
    - **Property 7: Stock Addition Persistence**
    - **Property 8: Save Data Completeness**
    - **Property 9: Invalid Save Rejection**
    - **Validates: Requirements 3.1, 3.4, 3.5, 4.5, 5.3, 5.4**

- [x] 2. Checkpoint - 后端服务测试
  - 确保所有属性测试通过
  - 如有问题请询问用户

- [x] 3. 创建后端 API 路由
  - [x] 3.1 创建存档 API 路由
    - 创建 `api/routers/saves.py`
    - 实现 GET `/api/saves/` 列出存档
    - 实现 POST `/api/saves/` 创建存档
    - 实现 GET `/api/saves/{save_id}` 获取存档
    - 实现 PUT `/api/saves/{save_id}` 更新存档
    - 实现 DELETE `/api/saves/{save_id}` 删除存档
    - _Requirements: 1.1, 2.2, 4.1, 6.2_

  - [x] 3.2 实现股票添加 API
    - 实现 POST `/api/saves/{save_id}/stocks` 添加股票
    - _Requirements: 5.3, 5.4_

  - [x] 3.3 注册路由到主应用
    - 更新 `api/main.py` 注册 saves 路由
    - _Requirements: 1.1_

  - [x] 3.4 更新 DataEngine 使用新的存储路径
    - 修改 DataEngine 使用 `storage/stock_data/` 目录
    - _Requirements: 7.1_

- [x] 4. Checkpoint - API 测试
  - 手动测试 API 端点
  - 如有问题请询问用户

- [x] 5. 创建前端类型和 API 服务
  - [x] 5.1 添加存档相关类型定义
    - 更新 `frontend/src/types/index.ts`
    - 添加 SaveMetadata、SaveData 接口
    - _Requirements: 1.2_

  - [x] 5.2 创建存档 API 服务
    - 创建 `frontend/src/services/saveApi.ts`
    - 实现 listSaves、createSave、loadSave、updateSave、deleteSave、addStock 方法
    - _Requirements: 1.1, 2.2, 4.1, 5.3, 6.2_

- [x] 6. 创建前端主页（存档列表）
  - [x] 6.1 创建主页组件
    - 创建 `frontend/src/pages/HomePage.tsx`
    - 显示存档列表
    - 实现新建存档按钮和弹窗
    - 实现删除存档功能
    - _Requirements: 1.1, 1.2, 1.3, 2.1, 2.2, 6.1, 6.2_

  - [x] 6.2 更新路由配置
    - 更新 `frontend/src/App.tsx` 路由
    - 设置主页为默认路由
    - _Requirements: 1.4_

- [x] 7. 更新交易页面支持存档
  - [x] 7.1 添加股票添加功能
    - 在 TradingView 添加"添加股票"按钮
    - 创建股票搜索弹窗组件
    - 实现添加股票到存档功能
    - _Requirements: 5.1, 5.2, 5.5_

  - [x] 7.2 实现自动保存功能
    - 在交易、状态变化时自动保存
    - _Requirements: 3.2, 3.3_

  - [x] 7.3 更新 TradingView 使用存档数据
    - 修改 TradingView 从存档加载数据
    - 支持空股票列表初始状态
    - _Requirements: 2.5, 4.2, 4.3, 4.4_

- [x] 8. Final Checkpoint - 集成测试
  - 测试完整的存档创建-加载-交易-保存流程
  - 如有问题请询问用户

## Notes

- 所有任务均为必需，包括属性测试
- 后端使用 Python + FastAPI
- 前端使用 React + TypeScript + Ant Design
- 属性测试使用 Hypothesis 库
- 所有数据存储在 `storage/` 目录下
