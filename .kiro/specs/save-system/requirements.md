# Requirements Document

## Introduction

本文档定义了A股模拟交易系统的存档机制需求。该功能允许用户创建、命名、保存和加载游戏存档，使用户能够在不同时间继续之前的交易模拟。所有数据统一存储在根目录下的 `storage` 文件夹中，包括用户存档和股票数据缓存。

## Glossary

- **Save_System**: 存档系统，负责管理存档的创建、保存、加载和删除
- **Save_File**: 存档文件，包含游戏状态的JSON文件，存放在 `storage/saves/` 目录
- **Save_Metadata**: 存档元数据，包含存档名称、创建时间、最后修改时间等信息
- **Stock_Data**: 股票数据，包含股票代码、历史K线数据、分时数据等，存放在 `storage/stock_data/` 目录
- **Game_State**: 游戏状态，包含当前日期、播放状态、账户信息等
- **Storage_Directory**: 存储根目录，位于项目根目录下的 `storage` 文件夹

## Requirements

### Requirement 1: 存档列表展示

**User Story:** As a user, I want to see a list of my saved games on the home page, so that I can choose to continue a previous game or start a new one.

#### Acceptance Criteria

1. WHEN a user visits the home page, THE Save_System SHALL display a list of all existing saves from the Storage_Directory
2. WHEN displaying saves, THE Save_System SHALL show save name, creation time, last modified time, and current simulation date for each save
3. IF no saves exist, THEN THE Save_System SHALL display an empty state with a prompt to create a new save
4. WHEN a save is selected, THE Save_System SHALL navigate the user directly to the trading page with that save loaded

### Requirement 2: 创建新存档

**User Story:** As a user, I want to create a new save with a custom name, so that I can start a fresh trading simulation and easily identify it later.

#### Acceptance Criteria

1. WHEN a user clicks the "new save" button, THE Save_System SHALL prompt the user to enter a save name
2. WHEN a user submits a valid save name, THE Save_System SHALL create a new save file in the Storage_Directory
3. WHEN a user attempts to create a save with an empty name, THE Save_System SHALL reject the creation and display an error message
4. WHEN a user attempts to create a save with a duplicate name, THE Save_System SHALL reject the creation and display an error message
5. WHEN a new save is created successfully, THE Save_System SHALL navigate the user to the trading page with an empty portfolio (no stocks)

### Requirement 3: 存档数据持久化

**User Story:** As a user, I want my game progress to be automatically saved, so that I don't lose my trading history and portfolio state.

#### Acceptance Criteria

1. WHEN a user adds a stock to their portfolio, THE Save_System SHALL persist the stock code and all necessary stock data to the save file
2. WHEN a user executes a trade, THE Save_System SHALL update the save file with the new account state
3. WHEN the game state changes (date advance, playback state), THE Save_System SHALL update the save file
4. THE Save_System SHALL store all data in JSON format within the Storage_Directory
5. WHEN saving data, THE Save_System SHALL include: account info, positions, stock codes, current date, playback state, and trade history

### Requirement 4: 加载存档

**User Story:** As a user, I want to load a previously saved game, so that I can continue my trading simulation from where I left off.

#### Acceptance Criteria

1. WHEN a user selects a save from the list, THE Save_System SHALL load all saved data from the save file
2. WHEN loading a save, THE Save_System SHALL restore the account state including cash, positions, and total assets
3. WHEN loading a save, THE Save_System SHALL restore the game state including current date and playback state
4. WHEN loading a save, THE Save_System SHALL load all stock data for stocks in the portfolio
5. IF a save file is corrupted or invalid, THEN THE Save_System SHALL display an error message and prevent loading

### Requirement 5: 动态添加股票

**User Story:** As a user, I want to add stocks to my portfolio from the trading page, so that I can track and trade multiple stocks within a single save.

#### Acceptance Criteria

1. WHEN a user is on the trading page, THE Save_System SHALL provide a toolbar option to add new stocks
2. WHEN a user searches for a stock to add, THE Save_System SHALL display matching results
3. WHEN a user selects a stock to add, THE Save_System SHALL fetch and cache all necessary stock data
4. WHEN a stock is added, THE Save_System SHALL persist the stock data to the save file immediately
5. WHEN a stock is added, THE Save_System SHALL update the UI to show the new stock in the stock selector

### Requirement 6: 删除存档

**User Story:** As a user, I want to delete saves I no longer need, so that I can keep my save list organized.

#### Acceptance Criteria

1. WHEN a user clicks the delete button on a save, THE Save_System SHALL prompt for confirmation
2. WHEN a user confirms deletion, THE Save_System SHALL remove the save file from the Storage_Directory
3. WHEN a save is deleted, THE Save_System SHALL update the save list immediately
4. IF deletion fails, THEN THE Save_System SHALL display an error message and keep the save in the list

### Requirement 7: 存档文件结构

**User Story:** As a developer, I want a well-defined save file structure, so that saves can be reliably read and written.

#### Acceptance Criteria

1. THE Save_System SHALL store all data under the `storage` directory with subdirectories for saves and stock data
2. THE Save_System SHALL store each save as a separate JSON file in the `storage/saves/` directory
3. THE Save_System SHALL use the save name (sanitized) as the filename with `.json` extension
4. THE Save_System SHALL include a version field in the save file for future compatibility
5. WHEN reading a save file, THE Save_System SHALL validate the file structure before loading
6. THE Save_System SHALL store stock market data in the `storage/stock_data/` directory, shared across all saves
