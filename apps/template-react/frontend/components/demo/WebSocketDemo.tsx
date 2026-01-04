'use client';

import { useEffect, useRef, useState } from 'react';
import { useTranslations } from 'next-intl';
import { io, type Socket } from 'socket.io-client';

import { DemoSection } from './DemoSection';
import { Button } from '@/components/ui/button';
import { getSocketOptions } from '@/config/kubb-config';

type State = 'connecting' | 'connected' | 'disconnected' | 'reconnecting';

interface Event {
  user: string;
  delta: number;
  time: string;
}

interface UpdatePayload {
  counter: number;
  users: number;
  events: Event[];
}

function formatTimeAgo(isoTime: string): string {
  const seconds = Math.floor((Date.now() - new Date(isoTime).getTime()) / 1000);
  if (seconds < 5) return 'now';
  if (seconds < 60) return `${String(seconds)}s ago`;
  const minutes = Math.floor(seconds / 60);
  return `${String(minutes)}m ago`;
}

function formatDelta(delta: number): string {
  return delta > 0 ? `+${String(delta)}` : String(delta);
}

export function WebSocketDemo() {
  const t = useTranslations('demo.websocket');
  const [state, setState] = useState<State>('disconnected');
  const [counter, setCounter] = useState(0);
  const [users, setUsers] = useState(0);
  const [events, setEvents] = useState<Event[]>([]);
  const [reconnectAttempt, setReconnectAttempt] = useState(0);
  const socketRef = useRef<Socket | null>(null);

  // Update time display every second
  const [, setTick] = useState(0);
  useEffect(() => {
    const interval = setInterval(() => {
      setTick(t => t + 1);
    }, 1000);
    return () => {
      clearInterval(interval);
    };
  }, []);

  useEffect(() => {
    const { url, options } = getSocketOptions();
    const socket = io(url, options);
    socketRef.current = socket;
    setState('connecting');

    socket.on('connect', () => {
      setState('connected');
      setReconnectAttempt(0);
    });

    socket.on('disconnect', () => {
      setState('disconnected');
    });

    socket.on('reconnect_attempt', (attempt: number) => {
      setState('reconnecting');
      setReconnectAttempt(attempt);
    });

    socket.on('update', (data: UpdatePayload) => {
      setCounter(data.counter);
      setUsers(data.users);
      setEvents(data.events);
    });

    return () => {
      socket.disconnect();
    };
  }, []);

  const sendDelta = (delta: number) => {
    socketRef.current?.emit('increment', delta);
  };

  const stateIcon = {
    connecting: '🟡',
    connected: '🟢',
    disconnected: '🔴',
    reconnecting: '🟠',
  }[state];

  const stateText = state === 'reconnecting'
    ? `${state} (${String(reconnectAttempt)})`
    : state;

  return (
    <DemoSection icon="&#128268;" title={t('title')}>
      <div className="space-y-4">
        <div className="text-sm">
          {stateIcon} {stateText}
        </div>

        {/* Counter display */}
        <div className="bg-muted rounded-lg p-4 text-center">
          <p className="text-4xl font-mono font-bold">{counter}</p>
          <p className="text-xs text-muted-foreground mt-1">{users} {t('usersOnline')}</p>
        </div>

        {/* Action buttons */}
        <div className="flex gap-2 justify-center">
          <Button
            size="sm"
            variant="outline"
            onClick={() => { sendDelta(-1); }}
            disabled={state !== 'connected'}
          >
            -1
          </Button>
          <Button
            size="sm"
            onClick={() => { sendDelta(1); }}
            disabled={state !== 'connected'}
          >
            +1
          </Button>
          <Button
            size="sm"
            onClick={() => { sendDelta(3); }}
            disabled={state !== 'connected'}
          >
            +3
          </Button>
        </div>

        {/* Recent events */}
        {events.length > 0 && (
          <div className="space-y-1">
            <p className="text-xs font-medium text-muted-foreground">Recent activity</p>
            <div className="bg-muted/50 rounded-lg p-2 space-y-1">
              {events.slice().reverse().map((event, idx) => (
                <div
                  key={`${event.time}-${String(idx)}`}
                  className="flex items-center justify-between text-xs"
                >
                  <span className="font-medium">{event.user}</span>
                  <span className={event.delta > 0 ? 'text-green-600' : 'text-red-600'}>
                    {formatDelta(event.delta)}
                  </span>
                  <span className="text-muted-foreground w-12 text-right">
                    {formatTimeAgo(event.time)}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        <p className="text-xs text-muted-foreground">
          {t('note')}
        </p>
      </div>
    </DemoSection>
  );
}
