<script setup>
import { computed } from 'vue'
import { RouterLink, RouterView, useRoute } from 'vue-router'

const route = useRoute()
const isAuthPage = computed(() => route.name === 'login' || route.name === 'signup' || route.name === 'kakao-callback')
</script>

<template>
  <div class="app-shell">
    <header class="site-header">
      <div class="site-header__inner">
        <RouterLink class="brand" :to="{ name: 'property-list' }" aria-label="Haven homes">
          <span class="brand-mark" aria-hidden="true"><svg viewBox="0 0 36 36" fill="none"><path d="m5 17 13-11 13 11v14H5V17Z" fill="currentColor"/><path d="M14 31V19h8v12M5 17l13-11 13 11" stroke="#F4F7F5" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg></span>
          <span class="brand-name">Haven<span> homes</span></span>
        </RouterLink>
        <nav class="header-nav" aria-label="Main navigation"><RouterLink :to="{ name: 'property-list' }">Explore homes</RouterLink><RouterLink :to="{ name: 'login' }">Sign in</RouterLink></nav>
        <RouterLink class="header-create" :to="{ name: 'property-create' }"><svg viewBox="0 0 20 20" aria-hidden="true"><path d="M10 4v12M4 10h12" /></svg><span>List a home</span></RouterLink>
      </div>
    </header>
    <main class="main-content" :class="{ 'main-content--auth': isAuthPage }"><RouterView v-slot="{ Component }"><Transition name="page" mode="out-in"><component :is="Component" /></Transition></RouterView></main>
    <footer class="site-footer"><RouterLink class="footer-brand" :to="{ name: 'property-list' }">Haven homes</RouterLink><span>Thoughtful homes for the next chapter.</span><span class="footer-copy">Find your place, at your own pace.</span></footer>
  </div>
</template>
