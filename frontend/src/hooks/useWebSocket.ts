/**
 * WebSocket Hook - 修复版本
 */
import { useEffect, useRef, useCallback, useState } from 'react';
import type { WSMessage, TickData, AccountUpdateData, StateUpdateData } from '../types';

interface UseWebSocketOptions {
  sessionId: string;
  onTick?: (data: TickData) => void;
  onAccountUpdate?: (data: AccountUpdateData) => void;
  onStateUpdate?: (data: StateUpdateData) => void;
  onDayEnd?: (date: string) => void;
  onError?: (message: string) => void;
}

interface UseWebSocketReturn {
  isConnected: boolean;
  play: (speed: number) => void;
  pause: () => void;
  tick: () => void;
  getState: () => void;
}

export function useWebSocket(options: UseWebSocketOptions): UseWebSocketReturn {
  const { sessionId } = options;
  const wsRef = useRef<WebSocket | null>(null);
  const [isConnected, setIsConnected] = useState(false);
  
  // 使用 ref 存储回调，避免重新连接
  const callbacksRef = useRef(options);
  callbacksRef.current = options;

  // 建立连接 - 只依赖 sessionId
  useEffect(() => {
    if (!sessionId) return;

    // 使用相对路径，让 Vite 代理处理
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const host = window.location.host;
    const wsUrl = `${protocol}//${host}/ws/playback/${sessionId}`;

    console.log('Creating WebSocket connection to:', wsUrl);
    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;

    ws.onopen = () => {
      console.log('WebSocket connected');
      setIsConnected(true);
    };

    ws.onclose = (event) => {
      console.log('WebSocket disconnected:', event.code, event.reason);
      setIsConnected(false);
    };

    ws.onerror = (error) => {
      console.error('WebSocket error:', error);
      callbacksRef.current.onError?.('WebSocket 连接错误');
    };

    ws.onmessage = (event) => {
      try {
        const message: WSMessage = JSON.parse(event.data);
        console.log('WebSocket message:', message.type, message.data);
        
        switch (message.type) {
          case 'tick':
            callbacksRef.current.onTick?.(message.data as unknown as TickData);
            break;
          case 'account_update':
            callbacksRef.current.onAccountUpdate?.(message.data as unknown as AccountUpdateData);
            break;
          case 'state_update':
          case 'state_change':
            callbacksRef.current.onStateUpdate?.(message.data as unknown as StateUpdateData);
            break;
          case 'day_end':
            callbacksRef.current.onDayEnd?.((message.data as { date: string }).date);
            break;
          case 'error':
            callbacksRef.current.onError?.((message.data as { message: string }).message);
            break;
        }
      } catch (e) {
        console.error('Failed to parse WebSocket message:', e);
      }
    };

    return () => {
      console.log('Closing WebSocket connection');
      ws.close();
    };
  }, [sessionId]); // 只依赖 sessionId

  // 发送消息
  const sendMessage = useCallback((message: Record<string, unknown>) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      console.log('Sending WebSocket message:', message);
      wsRef.current.send(JSON.stringify(message));
    } else {
      console.warn('WebSocket not connected, cannot send:', message);
    }
  }, []);

  // 播放
  const play = useCallback((speed: number) => {
    sendMessage({ action: 'play', speed });
  }, [sendMessage]);

  // 暂停
  const pause = useCallback(() => {
    sendMessage({ action: 'pause' });
  }, [sendMessage]);

  // 单步
  const tick = useCallback(() => {
    sendMessage({ action: 'tick' });
  }, [sendMessage]);

  // 获取状态
  const getState = useCallback(() => {
    sendMessage({ action: 'get_state' });
  }, [sendMessage]);

  return {
    isConnected,
    play,
    pause,
    tick,
    getState,
  };
}
