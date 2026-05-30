<template>
  <v-container class="mt-10" style="max-width: 500px;">

    <v-snackbar v-model="showPopup" color="success" location="top" timeout="5000">
      <v-icon icon="mdi-email-check" class="mr-2"></v-icon>
      Регистрация успешна! Письмо с ключом отправлено.
    </v-snackbar>

    <v-card class="pa-6" elevation="3">
      <v-card-title class="text-h5 text-center font-weight-bold text-primary mb-4">Регистрация</v-card-title>

      <v-form @submit.prevent="handleRegister">
        <v-text-field
          v-model="email"
          label="Email"
          type="email"
          variant="outlined"
          prepend-inner-icon="mdi-email"
          required
        ></v-text-field>

        <v-text-field
          v-model="password"
          label="Пароль"
          type="password"
          variant="outlined"
          prepend-inner-icon="mdi-lock"
          required
          class="mt-2"
        ></v-text-field>

        <v-text-field
          v-model="passwordConfirm"
          label="Повторите пароль"
          type="password"
          variant="outlined"
          prepend-inner-icon="mdi-lock-check"
          required
          class="mt-2"
          :error-messages="passwordError"
        ></v-text-field>

        <v-btn type="submit" color="primary" size="large" block class="mt-4" :loading="isLoading">
          Создать аккаунт
        </v-btn>
      </v-form>

      <div class="text-center mt-4">
        <v-btn variant="text" color="secondary" to="/login">Уже есть аккаунт? Войти</v-btn>
      </div>

      <v-alert v-if="errorMessage" type="error" class="mt-4" variant="tonal">{{ errorMessage }}</v-alert>
    </v-card>
  </v-container>
</template>

<script setup>
import { ref, computed } from 'vue';
import { useRouter } from 'vue-router';

const router = useRouter();
const email = ref('');
const password = ref('');
const passwordConfirm = ref('');

const errorMessage = ref('');
const isLoading = ref(false);
const showPopup = ref(false);

const passwordError = computed(() => {
  if (passwordConfirm.value && password.value !== passwordConfirm.value) {
    return 'Пароли не совпадают';
  }
  return '';
});

const handleRegister = async () => {
  if (password.value !== passwordConfirm.value) {
    errorMessage.value = 'Пароли не совпадают!';
    return;
  }

  isLoading.value = true;
  errorMessage.value = '';

  try {
    const response = await fetch('http://localhost:8000/register', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        email: email.value,
        password: password.value,
        password_confirm: passwordConfirm.value
      })
    });

    const data = await response.json();

    if (!response.ok) throw new Error(data.detail || 'Ошибка при регистрации');

    showPopup.value = true;
    password.value = '';
    passwordConfirm.value = '';

    setTimeout(() => {
      router.push('/login');
    }, 3000);

  } catch (error) {
    errorMessage.value = error.message;
  } finally {
    isLoading.value = false;
  }
};
</script>