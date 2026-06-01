<template>
  <v-container class="mt-10 mx-auto" max-width="500">
    <v-card class="pa-6" elevation="3">
      <v-card-title class="text-h5 text-center font-weight-bold text-primary mb-4">Вход в кабинет</v-card-title>

      <v-form @submit.prevent="handleLogin">
        <v-text-field v-model="email" label="Email" type="email" variant="outlined" prepend-inner-icon="mdi-email" required></v-text-field>
        <v-text-field v-model="password" label="Пароль" type="password" variant="outlined" prepend-inner-icon="mdi-lock" required class="mt-2"></v-text-field>

        <v-btn type="submit" color="primary" size="large" block class="mt-4" :loading="isLoading">Войти</v-btn>
      </v-form>

      <div class="text-center mt-4">
        <v-btn variant="text" color="secondary" to="/register">Нет аккаунта? Создать</v-btn>
      </div>

      <v-alert v-if="errorMessage" type="error" class="mt-4" variant="tonal">{{ errorMessage }}</v-alert>
    </v-card>
  </v-container>
</template>

<script setup>
import { ref } from 'vue';
import { useRouter } from 'vue-router';

const router = useRouter();
const email = ref('');
const password = ref('');
const errorMessage = ref('');
const isLoading = ref(false);

const handleLogin = async () => {
  isLoading.value = true;
  errorMessage.value = '';
  const apiUrl = import.meta.env.VITE_API_URL || 'http://localhost:8000';

  try {
    const response = await fetch(`${apiUrl}/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email: email.value, password: password.value })
    });
    const data = await response.json();

    if (!response.ok) throw new Error(data.detail || 'Ошибка авторизации');

    localStorage.setItem('userId', data.id);
    localStorage.setItem('userEmail', data.email);
    localStorage.setItem('activationKey', data.activation_key);

    router.push('/profile');
  } catch (error) {
    errorMessage.value = error.message;
  } finally {
    isLoading.value = false;
  }
};
</script>