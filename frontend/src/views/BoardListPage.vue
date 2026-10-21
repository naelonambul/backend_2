<script setup>
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { createApiClient } from '../api/api.js'
import { filterNotes, getCollectionCounts, getExcerpt, noteTone } from '../stores/notes.js'

const boards = ref([])
const loading = ref(true)
const error = ref('')
const query = ref('')
const activeCollection = ref('all')
const apiState = ref('idle')

const collections = [
  { id: 'all', label: '모든 기록', mark: '○' },
  { id: 'recent', label: '최근 추가', mark: '↗' },
  { id: 'short', label: '짧은 메모', mark: '—' },
  { id: 'long', label: '긴 글', mark: '≋' },
]

const counts = computed(() => getCollectionCounts(boards.value))
const visibleBoards = computed(() => filterNotes(boards.value, query.value, activeCollection.value))
const hasFilter = computed(() => Boolean(query.value.trim()) || activeCollection.value !== 'all')

function excerpt(contents) {
  return getExcerpt(contents, 118)
}

async function loadBoards() {
  loading.value = true
  error.value = ''
  try {
    boards.value = await createApiClient().listBoards()
    apiState.value = 'connected'
  } catch (requestError) {
    error.value = requestError.message || '기록을 불러오지 못했습니다.'
    apiState.value = 'offline'
  } finally {
    loading.value = false
  }
}

async function checkApi() {
  apiState.value = 'checking'
  try {
    await createApiClient().ping()
    apiState.value = 'connected'
  } catch {
    apiState.value = 'offline'
  }
}

function clearSearch() {
  query.value = ''
  activeCollection.value = 'all'
}

onMounted(loadBoards)
</script>

<template>
  <section class="library-page" aria-labelledby="library-title">
    <form class="note-search" role="search" @submit.prevent>
      <svg class="note-search__icon" viewBox="0 0 24 24" fill="none" aria-hidden="true">
        <circle cx="10.8" cy="10.8" r="6.8" />
        <path d="m16 16 4.2 4.2" />
      </svg>
      <input
        id="note-search"
        name="q"
        v-model="query"
        type="search"
        aria-label="기록 검색"
        placeholder="제목이나 글 속에서 찾아보기"
      />
      <button v-if="query" class="search-clear" type="button" aria-label="검색어 지우기" @click="query = ''">×</button>
      <span class="search-hint">찾기</span>
    </form>

    <nav class="collection-nav" aria-label="기록 모아 보기">
      <button
        v-for="collection in collections"
        :key="collection.id"
        class="collection-tab"
        :class="{ 'collection-tab--active': activeCollection === collection.id }"
        type="button"
        :aria-pressed="activeCollection === collection.id"
        @click="activeCollection = collection.id"
      >
        <span class="collection-tab__mark" aria-hidden="true">{{ collection.mark }}</span>
        <span>{{ collection.label }}</span>
        <span class="collection-tab__count">{{ counts[collection.id] }}</span>
      </button>
    </nav>

    <div class="library-intro">
      <div class="library-intro__copy">
        <p class="section-label">기록 보관함</p>
        <h1 id="library-title">적어 둔 생각을 다시 꺼내 볼 시간.</h1>
        <p v-if="query.trim()" class="library-description">“{{ query.trim() }}”에 맞는 기록 {{ visibleBoards.length }}개를 찾았어요.</p>
        <p v-else class="library-description">기억해 두고 싶은 마음과 생각을 한곳에서 찾아보세요.</p>
      </div>
      <div class="library-intro__tools">
        <div class="archive-total" aria-label="전체 기록 수">
          <span class="archive-total__number">{{ boards.length }}</span>
          <span class="archive-total__caption">개의 기록이<br />모였어요</span>
          <span class="archive-total__spark" aria-hidden="true">✳</span>
        </div>
        <button
          class="api-status"
          :class="'api-status--' + apiState"
          type="button"
          :disabled="apiState === 'checking'"
          @click="checkApi"
        >
          <span class="api-status__dot" aria-hidden="true"></span>
          {{ apiState === 'connected' ? '서버 연결됨' : apiState === 'offline' ? '서버 확인' : apiState === 'checking' ? '확인 중' : '서버 상태' }}
        </button>
        <button class="refresh-button" type="button" aria-label="기록 새로고침" @click="loadBoards">
          <svg viewBox="0 0 20 20" fill="none" aria-hidden="true">
            <path d="M16.6 8a6.8 6.8 0 0 0-11.9-2L3.3 7.4M3.3 7.4V3.8m0 3.6h3.6M3.4 12a6.8 6.8 0 0 0 11.9 2l1.4-1.4m0 0v3.6m0-3.6h-3.6" />
          </svg>
        </button>
      </div>
    </div>

    <div v-if="loading" class="note-grid" aria-busy="true" aria-label="기록을 불러오는 중">
      <div v-for="item in 3" :key="item" class="note-skeleton">
        <div class="note-skeleton__cover"></div>
        <div class="note-skeleton__line"></div>
        <div class="note-skeleton__line note-skeleton__line--short"></div>
      </div>
    </div>

    <div v-else-if="error" class="empty-panel empty-panel--error" role="alert">
      <span class="empty-panel__symbol" aria-hidden="true">!</span>
      <h3>기록을 가져오지 못했어요.</h3>
      <p>{{ error }}</p>
      <button class="text-button" type="button" @click="loadBoards">다시 불러오기</button>
    </div>

    <div v-else-if="visibleBoards.length" class="note-grid" aria-live="polite">
      <RouterLink
        v-for="board in visibleBoards"
        :key="board.idx"
        class="note-card"
        :to="{ name: 'board-detail', params: { idx: board.idx } }"
      >
        <div class="note-card__cover" :class="'note-card__cover--' + noteTone(board.idx)">
          <div class="note-card__cover-top">
            <span>모아 둔 기록</span>
            <span class="note-card__index">No. {{ String(board.idx).padStart(3, '0') }}</span>
          </div>
          <h3>{{ board.title }}</h3>
          <span class="note-card__bookmark" aria-hidden="true">
            <svg viewBox="0 0 28 34" fill="none">
              <path d="M5 3.5h18v27l-9-5.7-9 5.7v-27Z" />
            </svg>
          </span>
        </div>
        <div class="note-card__body">
          <p class="note-card__excerpt">{{ excerpt(board.contents) }}</p>
          <div class="note-card__footer">
            <span>{{ board.contents.trim().length }}자</span>
            <span class="note-card__open">열어 보기 <span aria-hidden="true">↗</span></span>
          </div>
        </div>
      </RouterLink>
    </div>

    <div v-else class="empty-panel">
      <span class="empty-panel__symbol" aria-hidden="true">✳</span>
      <h3>{{ hasFilter ? '이 조건에 맞는 기록이 없어요.' : '아직 모아 둔 기록이 없어요.' }}</h3>
      <p>{{ hasFilter ? '검색어나 모아 보기 기준을 바꿔 보세요.' : '첫 기록을 남기면 이곳에서 다시 만날 수 있어요.' }}</p>
      <button v-if="hasFilter" class="text-button" type="button" @click="clearSearch">모든 기록 보기</button>
      <RouterLink v-else class="button-primary" :to="{ name: 'board-create' }">첫 기록 남기기 <span aria-hidden="true">↗</span></RouterLink>
    </div>

    <div v-if="!loading && !error && visibleBoards.length" class="list-end">
      <span>모두 {{ visibleBoards.length }}개의 기록</span>
      <button v-if="hasFilter" class="text-button" type="button" @click="clearSearch">전체 기록 보기</button>
      <button v-else class="text-button" type="button" @click="loadBoards">새로고침</button>
    </div>
  </section>
</template>
