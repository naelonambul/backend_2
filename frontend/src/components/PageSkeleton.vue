<script setup>
defineProps({
  variant: { type: String, default: 'form' },
  compact: { type: Boolean, default: false },
})
</script>

<template>
  <section class="skeleton-page" :class="`skeleton-${variant}`" aria-busy="true" aria-label="페이지를 불러오는 중입니다">
    <div v-if="!compact" class="skeleton-heading">
      <span class="skeleton-block skeleton-kicker"></span>
      <span class="skeleton-block skeleton-title"></span>
      <span class="skeleton-block skeleton-subtitle"></span>
    </div>

    <template v-if="variant === 'list'">
      <div class="skeleton-toolbar"><span class="skeleton-block skeleton-small"></span><span class="skeleton-block skeleton-button"></span></div>
      <div class="skeleton-list">
        <article v-for="item in 4" :key="item" class="skeleton-card">
          <span class="skeleton-block skeleton-meta"></span>
          <span class="skeleton-block skeleton-row-title"></span>
          <span class="skeleton-block skeleton-row-copy"></span>
          <span class="skeleton-block skeleton-row-short"></span>
        </article>
      </div>
    </template>

    <template v-else-if="variant === 'detail'">
      <article class="skeleton-card skeleton-detail-card">
        <span class="skeleton-block skeleton-meta"></span>
        <span class="skeleton-block skeleton-row-title"></span>
        <span class="skeleton-block skeleton-row-copy"></span>
        <span class="skeleton-block skeleton-row-copy"></span>
        <span class="skeleton-block skeleton-row-copy"></span>
        <span class="skeleton-block skeleton-row-short"></span>
      </article>
    </template>

    <template v-else>
      <article class="skeleton-card skeleton-form-card">
        <span class="skeleton-block skeleton-meta"></span>
        <span class="skeleton-block skeleton-row-title"></span>
        <span class="skeleton-block skeleton-input"></span>
        <span class="skeleton-block skeleton-input"></span>
        <span v-if="variant === 'write'" class="skeleton-block skeleton-textarea"></span>
        <span class="skeleton-block skeleton-submit"></span>
      </article>
    </template>
  </section>
</template>
