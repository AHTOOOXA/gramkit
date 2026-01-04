<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { io, type Socket } from 'socket.io-client'

import { getSocketOptions } from '@/config/kubb-config'
import DemoSection from './DemoSection.vue'
import { Button } from '@/components/ui/button'

const { t } = useI18n()

type State = 'connecting' | 'connected' | 'disconnected' | 'reconnecting'

interface Event {
  user: string
  delta: number
  time: string
}

interface UpdatePayload {
  counter: number
  users: number
  events: Event[]
}

const state = ref<State>('disconnected')
const counter = ref(0)
const users = ref(0)
const events = ref<Event[]>([])
const reconnectAttempt = ref(0)
const socketRef = ref<Socket | null>(null)
const tick = ref(0)

const stateIcon = computed(() => {
  return {
    connecting: '🟡',
    connected: '🟢',
    disconnected: '🔴',
    reconnecting: '🟠',
  }[state.value]
})

const stateText = computed(() => {
  if (state.value === 'reconnecting') {
    return `${state.value} (${reconnectAttempt.value})`
  }
  return state.value
})

function formatTimeAgo(isoTime: string): string {
  const seconds = Math.floor((Date.now() - new Date(isoTime).getTime()) / 1000)
  if (seconds < 5) return 'now'
  if (seconds < 60) return `${String(seconds)}s ago`
  const minutes = Math.floor(seconds / 60)
  return `${String(minutes)}m ago`
}

function formatDelta(delta: number): string {
  return delta > 0 ? `+${String(delta)}` : String(delta)
}

function sendDelta(delta: number) {
  socketRef.value?.emit('increment', delta)
}

let intervalId: ReturnType<typeof setInterval> | null = null

onMounted(() => {
  // Update time display every second
  intervalId = setInterval(() => {
    tick.value += 1
  }, 1000)

  const { url, options } = getSocketOptions()
  const socket = io(url, options)
  socketRef.value = socket
  state.value = 'connecting'

  socket.on('connect', () => {
    state.value = 'connected'
    reconnectAttempt.value = 0
  })

  socket.on('disconnect', () => {
    state.value = 'disconnected'
  })

  socket.on('reconnect_attempt', (attempt: number) => {
    state.value = 'reconnecting'
    reconnectAttempt.value = attempt
  })

  socket.on('update', (data: UpdatePayload) => {
    counter.value = data.counter
    users.value = data.users
    events.value = data.events
  })
})

onUnmounted(() => {
  if (intervalId) {
    clearInterval(intervalId)
  }
  socketRef.value?.disconnect()
})
</script>

<template>
  <DemoSection icon="&#128268;" :title="t('demo.websocket.title')">
    <div class="space-y-4">
      <div class="text-sm">
        {{ stateIcon }} {{ stateText }}
      </div>

      <!-- Counter display -->
      <div class="bg-muted rounded-lg p-4 text-center">
        <p class="text-4xl font-mono font-bold">{{ counter }}</p>
        <p class="text-xs text-muted-foreground mt-1">{{ users }} {{ t('demo.websocket.usersOnline') }}</p>
      </div>

      <!-- Action buttons -->
      <div class="flex gap-2 justify-center">
        <Button
          size="sm"
          variant="outline"
          :disabled="state !== 'connected'"
          @click="sendDelta(-1)"
        >
          -1
        </Button>
        <Button
          size="sm"
          :disabled="state !== 'connected'"
          @click="sendDelta(1)"
        >
          +1
        </Button>
        <Button
          size="sm"
          :disabled="state !== 'connected'"
          @click="sendDelta(3)"
        >
          +3
        </Button>
      </div>

      <!-- Recent events -->
      <div v-if="events.length > 0" class="space-y-1">
        <p class="text-xs font-medium text-muted-foreground">Recent activity</p>
        <div class="bg-muted/50 rounded-lg p-2 space-y-1">
          <div
            v-for="(event, idx) in events.slice().reverse()"
            :key="`${event.time}-${String(idx)}`"
            class="flex items-center justify-between text-xs"
          >
            <span class="font-medium">{{ event.user }}</span>
            <span :class="event.delta > 0 ? 'text-green-600' : 'text-red-600'">
              {{ formatDelta(event.delta) }}
            </span>
            <span class="text-muted-foreground w-12 text-right">
              {{ formatTimeAgo(event.time) }}
            </span>
          </div>
        </div>
      </div>

      <p class="text-xs text-muted-foreground">
        {{ t('demo.websocket.note') }}
      </p>
    </div>
  </DemoSection>
</template>
