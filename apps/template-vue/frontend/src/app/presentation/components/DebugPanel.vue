<script setup lang="ts">
import { ref } from 'vue';
import { usePlatformMock, injectMockInitData } from '@core/platform';

const platformMock = usePlatformMock();

// User selection for mock mode
const selectedUserId = ref(platformMock.selectedUser.value?.user_id || platformMock.availableUsers[0]?.user_id);

function onUserChange() {
  const selectedUser = platformMock.availableUsers.find(user => user.user_id === selectedUserId.value);
  if (selectedUser) {
    // Picking a user means "log in as" them — enable login-as ONLY. We never
    // touch TG mock here, so you can be a real user on the web platform.
    platformMock.isUserMockEnabled.value = true;
    platformMock.setSelectedUser(selectedUser);
    // Inject mock initData before reload so boot authenticates as this user.
    injectMockInitData(selectedUser);
  }
  window.location.reload();
}

// TG-platform mock: report platform as Telegram. Independent of who you are.
function onToggleMock() {
  platformMock.toggleMock();
  window.location.reload();
}

// Login-as mock: authenticate as the selected user. Independent of TG mock.
function onToggleUserMock() {
  platformMock.toggleUserMock();
  // Turning login-as on must inject the chosen user's initData before reload.
  if (platformMock.isUserMockEnabled.value) {
    const selectedUser = platformMock.availableUsers.find(user => user.user_id === selectedUserId.value)
      ?? platformMock.selectedUser.value;
    if (selectedUser) injectMockInitData(selectedUser);
  }
  window.location.reload();
}

// Only show in debug mode
const isDev = import.meta.env.VITE_DEBUG === 'true';
</script>

<template>
  <div v-if="isDev" class="fixed top-2 md:top-16 left-2 z-[9999] flex flex-col gap-1 text-xs">
    <!-- Debug mode indicator -->
    <div class="rounded bg-red-500 px-2 py-1 text-center font-medium text-white shadow">
      debug mode
    </div>

    <!-- TG-platform mock: telegram vs web. Independent of login-as. -->
    <button
      class="cursor-pointer rounded px-2 py-1 font-medium shadow transition-colors"
      :class="platformMock.isMockEnabled.value
        ? 'bg-green-500 text-white hover:bg-green-600'
        : 'bg-yellow-500 text-black hover:bg-yellow-600'"
      @click="onToggleMock()"
    >
      {{ platformMock.isMockEnabled.value ? '📱 TG Mock ON' : '🌐 TG Mock OFF' }}
    </button>

    <!-- Login-as mock: authenticate as the selected user. Independent of TG mock. -->
    <button
      class="cursor-pointer rounded px-2 py-1 font-medium shadow transition-colors"
      :class="platformMock.isUserMockEnabled.value
        ? 'bg-green-500 text-white hover:bg-green-600'
        : 'bg-yellow-500 text-black hover:bg-yellow-600'"
      @click="onToggleUserMock()"
    >
      {{ platformMock.isUserMockEnabled.value ? '👤 Login-as ON' : '👤 Login-as OFF' }}
    </button>

    <!-- User selector — always available; picking a user logs you in as them. -->
    <select
      v-if="platformMock.availableUsers.length > 0"
      v-model="selectedUserId"
      class="cursor-pointer rounded bg-blue-500 px-2 py-1 font-medium text-white shadow outline-none hover:bg-blue-600"
      @change="onUserChange"
    >
      <option
        v-for="user in platformMock.availableUsers"
        :key="user.user_id"
        :value="user.user_id"
        class="bg-gray-800"
      >
        {{ user.username }}
      </option>
    </select>
  </div>
</template>
