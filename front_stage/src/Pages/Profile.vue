<template>
  <v-container class="mt-10" style="max-width: 900px;">

    <v-snackbar v-model="snackbar.show" :color="snackbar.color" location="top" timeout="3000">
      {{ snackbar.text }}
    </v-snackbar>

    <v-row>
      <v-col cols="12" md="6">
        <v-card class="pa-6 rounded-lg h-100" elevation="3">
          <v-card-title class="text-h6 font-weight-bold text-primary mb-4">
            <v-icon icon="mdi-account-box" class="mr-2"></v-icon>Ваш профиль
          </v-card-title>

          <div class="mb-4">
            <span class="text-grey-darken-1 text-subtitle-2">Email:</span>
            <div class="text-h6 font-weight-medium">{{ userEmail }}</div>
          </div>

          <v-divider class="my-4"></v-divider>

          <div>
            <span class="text-grey-darken-1 text-subtitle-2">Ваш текущий ключ доступа:</span>
            <v-text-field
              v-model="activationKey"
              readonly
              variant="solo-filled"
              append-inner-icon="mdi-content-copy"
              @click:append-inner="copyToClipboard"
              class="mt-1 font-mono"
              messages="Ключ одноразовый. Обновится после использования."
            ></v-text-field>
          </div>

          <v-btn
            color="primary"
            block
            size="large"
            class="mt-4 font-weight-bold"
            prepend-icon="mdi-refresh"
            @click="handleRegenerateKey"
            :loading="isKeyLoading"
          >
            Сгенерировать новый
          </v-btn>
        </v-card>
      </v-col>

      <v-col cols="12" md="6">
        <v-row>
          <v-col cols="12">
            <v-card class="pa-6 rounded-lg" elevation="3">
              <v-card-title class="text-h6 font-weight-bold text-success mb-2">
                <v-icon icon="mdi-lan" class="mr-2"></v-icon>Статус сессии
              </v-card-title>

              <v-chip
                :color="isDesktopConnected ? 'success' : 'warning'"
                size="large"
                class="font-weight-bold w-100 justify-center py-4 mb-4"
              >
                <v-icon :icon="isDesktopConnected ? 'mdi-lan-connect' : 'mdi-lan-pending'" class="mr-2"></v-icon>
                {{ isDesktopConnected ? 'Десктоп подключен' : 'Ожидание подключения...' }}
              </v-chip>

              <!-- ДЕТАЛИ ВИРТУАЛКИ (показываются только при успешном коннекте) -->
              <v-list v-if="isDesktopConnected" density="compact" class="bg-grey-lighten-4 rounded">
                <v-list-item>
                  <template v-slot:prepend>
                    <v-icon icon="mdi-server" color="primary"></v-icon>
                  </template>
                  <v-list-item-title class="font-weight-medium">Название сервера</v-list-item-title>
                  <v-list-item-subtitle>{{ vmDetails.name }}</v-list-item-subtitle>
                </v-list-item>

                <v-list-item>
                  <template v-slot:prepend>
                    <v-icon icon="mdi-ip-network" color="primary"></v-icon>
                  </template>
                  <v-list-item-title class="font-weight-medium">Хост (IP)</v-list-item-title>
                  <v-list-item-subtitle class="font-mono">{{ vmDetails.host }}</v-list-item-subtitle>
                </v-list-item>

                <v-list-item>
                  <template v-slot:prepend>
                    <v-icon icon="mdi-door-open" color="primary"></v-icon>
                  </template>
                  <v-list-item-title class="font-weight-medium">Порт</v-list-item-title>
                  <v-list-item-subtitle class="font-mono">{{ vmDetails.port }}</v-list-item-subtitle>
                </v-list-item>

                <v-list-item>
                  <template v-slot:prepend>
                    <v-icon icon="mdi-shield-link-variant" color="primary"></v-icon>
                  </template>
                  <v-list-item-title class="font-weight-medium">Протокол</v-list-item-title>
                  <v-list-item-subtitle class="text-uppercase">{{ vmDetails.protocol }}</v-list-item-subtitle>
                </v-list-item>
              </v-list>

            </v-card>
          </v-col>

          <v-col cols="12">
            <v-card class="pa-6 rounded-lg" elevation="3">
              <v-card-title class="text-h6 font-weight-bold text-secondary mb-4">
                <v-icon icon="mdi-lock-reset" class="mr-2"></v-icon>Смена пароля
              </v-card-title>

              <v-form @submit.prevent="handleChangePassword">
                <v-text-field v-model="oldPassword" label="Текущий пароль" type="password" variant="outlined" density="compact" required></v-text-field>
                <v-text-field v-model="newPassword" label="Новый пароль" type="password" variant="outlined" density="compact" required class="mt-2"></v-text-field>

                <v-btn type="submit" color="secondary" block class="mt-2 font-weight-bold" :loading="isPassLoading">
                  Сохранить
                </v-btn>
              </v-form>
            </v-card>
          </v-col>
        </v-row>
      </v-col>
    </v-row>

    <div class="text-center mt-6">
      <v-btn color="error" variant="tonal" size="large" @click="logout" prepend-icon="mdi-logout">
        Выйти из аккаунта
      </v-btn>
    </div>

  </v-container>
</template>

<script setup>
import { ref, reactive, onMounted, onUnmounted } from 'vue';
import { useRouter } from 'vue-router';

const router = useRouter();

const userId = ref('');
const userEmail = ref('');
const activationKey = ref('');

const isKeyLoading = ref(false);
const isPassLoading = ref(false);

const oldPassword = ref('');
const newPassword = ref('');

const snackbar = reactive({ show: false, text: '', color: 'success' });
const showMessage = (text, color = 'success') => {
  snackbar.text = text;
  snackbar.color = color;
  snackbar.show = true;
};

const isDesktopConnected = ref(false);
const vmDetails = reactive({
  name: '',
  host: '',
  port: '',
  protocol: ''
});
let wsConnection = null;

onMounted(() => {
  userId.value = localStorage.getItem('userId');
  userEmail.value = localStorage.getItem('userEmail');
  activationKey.value = localStorage.getItem('activationKey');

  if (!userId.value) {
    router.push('/login');
  } else {
    initWebSocket();
  }
});

onUnmounted(() => {
  if (wsConnection) {
    wsConnection.close();
  }
});

const initWebSocket = () => {
  wsConnection = new WebSocket(`ws://localhost:8000/ws/connection-status/${userId.value}`);

  wsConnection.onmessage = (event) => {
    const data = JSON.parse(event.data);

    if (data.status === 'connected') {
      isDesktopConnected.value = true;

      vmDetails.name = data.vm_data.name;
      vmDetails.host = data.vm_data.host;
      vmDetails.port = data.vm_data.port;
      vmDetails.protocol = data.vm_data.protocol;

      activationKey.value = data.new_key;
      localStorage.setItem('activationKey', data.new_key);

      showMessage('Приложение успешно подключено!', 'success');
    } else if (data.status === 'disconnected') {

      isDesktopConnected.value = false;
      showMessage('Приложение отключено.', 'warning');
    }

  };

  wsConnection.onclose = () => {
    console.log('WebSocket отключен');
    isDesktopConnected.value = false;
  };
};

const copyToClipboard = () => {
  navigator.clipboard.writeText(activationKey.value);
  showMessage('Ключ скопирован в буфер обмена!');
};

const handleRegenerateKey = async () => {
  isKeyLoading.value = true;
  try {
    const response = await fetch(`http://localhost:8000/users/${userId.value}/regenerate-key`, {
      method: 'POST'
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || 'Не удалось обновить ключ');

    activationKey.value = data.activation_key;
    localStorage.setItem('activationKey', data.activation_key);

    isDesktopConnected.value = false;

    showMessage('Сгенерирован новый ключ! Письмо отправлено на почту.');
  } catch (error) {
    showMessage(error.message, 'error');
  } finally {
    isKeyLoading.value = false;
  }
};

const handleChangePassword = async () => {
  isPassLoading.value = true;
  try {
    const response = await fetch(`http://localhost:8000/users/${userId.value}/change-password`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ old_password: oldPassword.value, new_password: newPassword.value })
    });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || 'Ошибка смены пароля');

    showMessage('Пароль успешно изменен!');
    oldPassword.value = '';
    newPassword.value = '';
  } catch (error) {
    showMessage(error.message, 'error');
  } finally {
    isPassLoading.value = false;
  }
};

const logout = () => {
  if (wsConnection) wsConnection.close();
  localStorage.clear();
  router.push('/login');
};
</script>