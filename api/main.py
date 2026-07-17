"""
A股模拟交易系统 - FastAPI 后端服务
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routers import stocks, game, websocket, saves, achievements, t_trades, challenges, leaderboard, indicators

app = FastAPI(
    title="A股模拟交易系统",
    description="基于 AkShare 的 A 股模拟交易回测系统 API",
    version="1.0.0"
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(stocks.router)
app.include_router(game.router)
app.include_router(websocket.router)
app.include_router(saves.router)
app.include_router(achievements.router)
app.include_router(t_trades.router)
app.include_router(challenges.router)
app.include_router(leaderboard.router)
app.include_router(indicators.router)


@app.get("/")
async def root():
    """API 根路径"""
    return {"message": "A股模拟交易系统 API", "version": "1.0.0"}


@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy"}
