<template>
  <div class="app">
    <!-- Sidebar -->
    <aside class="sidebar" :class="{ collapsed: isCollapsed }">
      <div class="sidebar-header">
        <div class="sidebar-logo-full">
          <span class="logo-name">{{ t('nav.companyName') }}</span>
          <span class="logo-sub">{{ t('nav.subtitle') }}</span>
        </div>
        <span class="logo-initial">{{ t('nav.companyName').charAt(0) }}</span>
        <button class="collapse-toggle" @click="toggleCollapse" :title="isCollapsed ? 'Expand sidebar' : 'Collapse sidebar'">
          <svg viewBox="0 0 20 20" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
            <polyline v-if="isCollapsed" points="7,4 13,10 7,16"/>
            <polyline v-else points="13,4 7,10 13,16"/>
          </svg>
        </button>
      </div>

      <nav class="sidebar-nav">
        <router-link to="/" class="nav-item" :class="{ active: $route.path === '/' }">
          <svg class="nav-icon" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.5">
            <rect x="2" y="2" width="6" height="6" rx="1"/>
            <rect x="12" y="2" width="6" height="6" rx="1"/>
            <rect x="2" y="12" width="6" height="6" rx="1"/>
            <rect x="12" y="12" width="6" height="6" rx="1"/>
          </svg>
          <span class="nav-label">{{ t('nav.overview') }}</span>
        </router-link>

        <router-link to="/inventory" class="nav-item" :class="{ active: $route.path === '/inventory' }">
          <svg class="nav-icon" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
            <path d="M10 2L3 6v8l7 4 7-4V6L10 2z"/>
            <line x1="10" y1="2" x2="10" y2="18"/>
            <line x1="3" y1="6" x2="17" y2="6"/>
          </svg>
          <span class="nav-label">{{ t('nav.inventory') }}</span>
        </router-link>

        <router-link to="/orders" class="nav-item" :class="{ active: $route.path === '/orders' }">
          <svg class="nav-icon" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round">
            <line x1="3" y1="5" x2="17" y2="5"/>
            <line x1="3" y1="10" x2="17" y2="10"/>
            <line x1="3" y1="15" x2="17" y2="15"/>
          </svg>
          <span class="nav-label">{{ t('nav.orders') }}</span>
        </router-link>

        <router-link to="/spending" class="nav-item" :class="{ active: $route.path === '/spending' }">
          <svg class="nav-icon" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round">
            <circle cx="10" cy="10" r="8"/>
            <path d="M10 6.5v1M10 12.5v1M8.2 8.8c.2-.8 1-.8 1.8-.8s1.8.2 1.8 1-.7 1-1.8 1-1.8.2-1.8 1 .7 1.2 1.8 1.2 1.6-.2 1.8-.8"/>
          </svg>
          <span class="nav-label">{{ t('nav.finance') }}</span>
        </router-link>

        <router-link to="/demand" class="nav-item" :class="{ active: $route.path === '/demand' }">
          <svg class="nav-icon" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
            <polyline points="2,16 7,10 12,12 18,4"/>
            <polyline points="14,4 18,4 18,8"/>
          </svg>
          <span class="nav-label">{{ t('nav.demandForecast') }}</span>
        </router-link>

        <router-link to="/restocking" class="nav-item" :class="{ active: $route.path === '/restocking' }">
          <svg class="nav-icon" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">
            <path d="M4.5 10a5.5 5.5 0 015.5-5.5c1.7 0 3.2.8 4.2 2"/>
            <path d="M15.5 10a5.5 5.5 0 01-5.5 5.5c-1.7 0-3.2-.8-4.2-2"/>
            <polyline points="14,4 14.5,7 17.5,6.5"/>
            <polyline points="6,16 5.5,13 2.5,13.5"/>
          </svg>
          <span class="nav-label">Restocking</span>
        </router-link>

        <router-link to="/reports" class="nav-item" :class="{ active: $route.path === '/reports' }">
          <svg class="nav-icon" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round">
            <line x1="2" y1="18" x2="18" y2="18"/>
            <rect x="3" y="12" width="3" height="6" rx="0.5"/>
            <rect x="8.5" y="8" width="3" height="10" rx="0.5"/>
            <rect x="14" y="4" width="3" height="14" rx="0.5"/>
          </svg>
          <span class="nav-label">Reports</span>
        </router-link>
      </nav>
    </aside>

    <!-- App body (right side) -->
    <div class="app-body">
      <div class="top-bar">
        <div class="filter-bar-wrap">
          <FilterBar />
        </div>
        <LanguageSwitcher />
        <ProfileMenu
          @show-profile-details="showProfileDetails = true"
          @show-tasks="showTasks = true"
        />
      </div>
      <main class="main-content">
        <router-view />
      </main>
    </div>

    <ProfileDetailsModal
      :is-open="showProfileDetails"
      @close="showProfileDetails = false"
    />

    <TasksModal
      :is-open="showTasks"
      :tasks="tasks"
      @close="showTasks = false"
      @add-task="addTask"
      @delete-task="deleteTask"
      @toggle-task="toggleTask"
    />
  </div>
</template>

<script>
import { ref, onMounted, computed } from 'vue'
import { api } from './api'
import { useAuth } from './composables/useAuth'
import { useI18n } from './composables/useI18n'
import FilterBar from './components/FilterBar.vue'
import ProfileMenu from './components/ProfileMenu.vue'
import ProfileDetailsModal from './components/ProfileDetailsModal.vue'
import TasksModal from './components/TasksModal.vue'
import LanguageSwitcher from './components/LanguageSwitcher.vue'

export default {
  name: 'App',
  components: {
    FilterBar,
    ProfileMenu,
    ProfileDetailsModal,
    TasksModal,
    LanguageSwitcher
  },
  setup() {
    const { currentUser } = useAuth()
    const { t } = useI18n()
    const showProfileDetails = ref(false)
    const showTasks = ref(false)
    const apiTasks = ref([])

    // Merge mock tasks from currentUser with API tasks
    const tasks = computed(() => {
      return [...currentUser.value.tasks, ...apiTasks.value]
    })

    const loadTasks = async () => {
      try {
        apiTasks.value = await api.getTasks()
      } catch (err) {
        console.error('Failed to load tasks:', err)
      }
    }

    const addTask = async (taskData) => {
      try {
        const newTask = await api.createTask(taskData)
        // Add new task to the beginning of the array
        apiTasks.value.unshift(newTask)
      } catch (err) {
        console.error('Failed to add task:', err)
      }
    }

    const deleteTask = async (taskId) => {
      try {
        // Check if it's a mock task (from currentUser)
        const isMockTask = currentUser.value.tasks.some(t => t.id === taskId)

        if (isMockTask) {
          // Remove from mock tasks
          const index = currentUser.value.tasks.findIndex(t => t.id === taskId)
          if (index !== -1) {
            currentUser.value.tasks.splice(index, 1)
          }
        } else {
          // Remove from API tasks
          await api.deleteTask(taskId)
          apiTasks.value = apiTasks.value.filter(t => t.id !== taskId)
        }
      } catch (err) {
        console.error('Failed to delete task:', err)
      }
    }

    const toggleTask = async (taskId) => {
      try {
        // Check if it's a mock task (from currentUser)
        const mockTask = currentUser.value.tasks.find(t => t.id === taskId)

        if (mockTask) {
          // Toggle mock task status
          mockTask.status = mockTask.status === 'pending' ? 'completed' : 'pending'
        } else {
          // Toggle API task
          const updatedTask = await api.toggleTask(taskId)
          const index = apiTasks.value.findIndex(t => t.id === taskId)
          if (index !== -1) {
            apiTasks.value[index] = updatedTask
          }
        }
      } catch (err) {
        console.error('Failed to toggle task:', err)
      }
    }

    onMounted(loadTasks)

    // --- Sidebar state ---
    const isCollapsed = ref(false)

    const initSidebar = () => {
      const isMobile = window.innerWidth <= 768
      if (isMobile) {
        isCollapsed.value = true
      } else {
        const saved = localStorage.getItem('sidebar-collapsed')
        isCollapsed.value = saved === 'true'
      }
    }

    const toggleCollapse = () => {
      isCollapsed.value = !isCollapsed.value
      localStorage.setItem('sidebar-collapsed', String(isCollapsed.value))
    }

    onMounted(initSidebar)

    return {
      t,
      showProfileDetails,
      showTasks,
      tasks,
      addTask,
      deleteTask,
      toggleTask,
      isCollapsed,
      toggleCollapse
    }
  }
}
</script>

<style>
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
  background: #f8fafc;
  color: #1e293b;
  -webkit-font-smoothing: antialiased;
  -moz-osx-font-smoothing: grayscale;
}

.app {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

.top-nav {
  background: #ffffff;
  border-bottom: 1px solid #e2e8f0;
  box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.05);
  position: sticky;
  top: 0;
  z-index: 100;
}

.nav-container {
  max-width: 1600px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  padding: 0 2rem;
  height: 70px;
}

.nav-container > .nav-tabs {
  margin-left: auto;
  margin-right: 1rem;
}

.nav-container > .language-switcher {
  margin-right: 1rem;
}

.logo {
  display: flex;
  align-items: baseline;
  gap: 0.75rem;
}

.logo h1 {
  font-size: 1.375rem;
  font-weight: 700;
  color: #0f172a;
  letter-spacing: -0.025em;
}

.subtitle {
  font-size: 0.813rem;
  color: #64748b;
  font-weight: 400;
  padding-left: 0.75rem;
  border-left: 1px solid #e2e8f0;
}

.nav-tabs {
  display: flex;
  gap: 0.25rem;
}

.nav-tabs a {
  padding: 0.625rem 1.25rem;
  color: #64748b;
  text-decoration: none;
  font-weight: 500;
  font-size: 0.938rem;
  border-radius: 6px;
  transition: all 0.2s ease;
  position: relative;
}

.nav-tabs a:hover {
  color: #0f172a;
  background: #f1f5f9;
}

.nav-tabs a.active {
  color: #2563eb;
  background: #eff6ff;
}

.nav-tabs a.active::after {
  content: '';
  position: absolute;
  bottom: -1px;
  left: 0;
  right: 0;
  height: 2px;
  background: #2563eb;
}

.main-content {
  flex: 1;
  max-width: 1600px;
  width: 100%;
  margin: 0 auto;
  padding: 1.5rem 2rem;
}

.page-header {
  margin-bottom: 1.5rem;
}

.page-header h2 {
  font-size: 1.875rem;
  font-weight: 700;
  color: #0f172a;
  margin-bottom: 0.375rem;
  letter-spacing: -0.025em;
}

.page-header p {
  color: #64748b;
  font-size: 0.938rem;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 1.25rem;
  margin-bottom: 1.5rem;
}

.stat-card {
  background: white;
  padding: 1.25rem;
  border-radius: 10px;
  border: 1px solid #e2e8f0;
  transition: all 0.2s ease;
}

.stat-card:hover {
  border-color: #cbd5e1;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.06);
}

.stat-label {
  color: #64748b;
  font-size: 0.875rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 0.625rem;
}

.stat-value {
  font-size: 2.25rem;
  font-weight: 700;
  color: #0f172a;
  letter-spacing: -0.025em;
}

.stat-card.warning .stat-value {
  color: #ea580c;
}

.stat-card.success .stat-value {
  color: #059669;
}

.stat-card.danger .stat-value {
  color: #dc2626;
}

.stat-card.info .stat-value {
  color: #2563eb;
}

.card {
  background: white;
  border-radius: 10px;
  padding: 1.25rem;
  border: 1px solid #e2e8f0;
  margin-bottom: 1.25rem;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
  padding-bottom: 0.875rem;
  border-bottom: 1px solid #e2e8f0;
}

.card-title {
  font-size: 1.125rem;
  font-weight: 700;
  color: #0f172a;
  letter-spacing: -0.025em;
}

.table-container {
  overflow-x: auto;
}

table {
  width: 100%;
  border-collapse: collapse;
}

thead {
  background: #f8fafc;
  border-top: 1px solid #e2e8f0;
  border-bottom: 1px solid #e2e8f0;
}

th {
  text-align: left;
  padding: 0.5rem 0.75rem;
  font-weight: 600;
  color: #475569;
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

td {
  padding: 0.5rem 0.75rem;
  border-top: 1px solid #f1f5f9;
  color: #334155;
  font-size: 0.875rem;
}

tbody tr {
  transition: background-color 0.15s ease;
}

tbody tr:hover {
  background: #f8fafc;
}

.badge {
  display: inline-block;
  padding: 0.313rem 0.75rem;
  border-radius: 6px;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.025em;
}

.badge.success {
  background: #d1fae5;
  color: #065f46;
}

.badge.warning {
  background: #fed7aa;
  color: #92400e;
}

.badge.danger {
  background: #fecaca;
  color: #991b1b;
}

.badge.info {
  background: #dbeafe;
  color: #1e40af;
}

.badge.increasing {
  background: #d1fae5;
  color: #065f46;
}

.badge.decreasing {
  background: #fecaca;
  color: #991b1b;
}

.badge.stable {
  background: #e0e7ff;
  color: #3730a3;
}

.badge.high {
  background: #fecaca;
  color: #991b1b;
}

.badge.medium {
  background: #fed7aa;
  color: #92400e;
}

.badge.low {
  background: #dbeafe;
  color: #1e40af;
}

.loading {
  text-align: center;
  padding: 3rem;
  color: #64748b;
  font-size: 0.938rem;
}

.error {
  background: #fef2f2;
  border: 1px solid #fecaca;
  color: #991b1b;
  padding: 1rem;
  border-radius: 8px;
  margin: 1rem 0;
  font-size: 0.938rem;
}
</style>

<style scoped>
/* Override global .app to use row layout for sidebar */
.app {
  flex-direction: row;
  align-items: stretch;
}

/* ── Sidebar ─────────────────────────────────────────────── */
.sidebar {
  width: 220px;
  min-width: 220px;
  background: #ffffff;
  border-right: 1px solid #e2e8f0;
  display: flex;
  flex-direction: column;
  height: 100vh;
  position: sticky;
  top: 0;
  flex-shrink: 0;
  overflow: hidden;
  transition: width 0.25s ease, min-width 0.25s ease;
  z-index: 100;
}

.sidebar.collapsed {
  width: 60px;
  min-width: 60px;
}

/* ── Sidebar header (logo + toggle) ─────────────────────── */
.sidebar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 0.875rem;
  height: 64px;
  border-bottom: 1px solid #e2e8f0;
  flex-shrink: 0;
  position: relative;
  overflow: hidden;
}

.sidebar-logo-full {
  display: flex;
  flex-direction: column;
  justify-content: center;
  flex: 1;
  overflow: hidden;
  min-width: 0;
  margin-right: 0.5rem;
}

.logo-name {
  font-size: 0.875rem;
  font-weight: 700;
  color: #0f172a;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  line-height: 1.2;
}

.logo-sub {
  font-size: 0.7rem;
  color: #94a3b8;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  margin-top: 2px;
  line-height: 1.2;
}

.logo-initial {
  display: none;
  font-size: 18px;
  font-weight: 700;
  color: #2563eb;
  line-height: 1;
}

.sidebar.collapsed .sidebar-logo-full {
  display: none;
}

.sidebar.collapsed .logo-initial {
  display: block;
}

.sidebar.collapsed .sidebar-header {
  justify-content: center;
}

.sidebar.collapsed .collapse-toggle {
  position: absolute;
  top: 8px;
  right: 8px;
}

/* Collapse toggle button */
.collapse-toggle {
  width: 28px;
  height: 28px;
  border-radius: 6px;
  border: 1px solid #e2e8f0;
  background: #ffffff;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  color: #64748b;
  transition: background 0.15s ease, border-color 0.15s ease;
  padding: 0;
}

.collapse-toggle:hover {
  background: #f1f5f9;
  border-color: #cbd5e1;
}

/* ── Sidebar nav ─────────────────────────────────────────── */
.sidebar-nav {
  display: flex;
  flex-direction: column;
  padding: 0.5rem 0;
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0 0.875rem;
  height: 44px;
  color: #64748b;
  text-decoration: none;
  font-size: 0.875rem;
  font-weight: 500;
  border-left: 3px solid transparent;
  transition: background 0.15s ease, color 0.15s ease, border-color 0.15s ease;
  white-space: nowrap;
  overflow: hidden;
}

.nav-item:hover {
  background: #f1f5f9;
  color: #0f172a;
}

.nav-item.active {
  background: #eff6ff;
  color: #2563eb;
  border-left-color: #2563eb;
}

.nav-icon {
  width: 20px;
  height: 20px;
  flex-shrink: 0;
}

.nav-label {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
}

/* Collapsed nav: centre icon, hide labels */
.sidebar.collapsed .nav-item {
  justify-content: center;
  padding: 0 0 0 3px; /* offset for border-left */
}

.sidebar.collapsed .nav-label {
  display: none;
}

/* ── App body (right side) ───────────────────────────────── */
.app-body {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

/* ── Top bar ─────────────────────────────────────────────── */
.top-bar {
  height: 52px;
  background: #ffffff;
  border-bottom: 1px solid #e2e8f0;
  display: flex;
  align-items: center;
  padding: 0 1.5rem;
  gap: 0.75rem;
  position: sticky;
  top: 0;
  z-index: 50;
  flex-shrink: 0;
}

.filter-bar-wrap {
  flex: 1;
  display: flex;
  align-items: center;
  min-width: 0;
  overflow: hidden;
}

/* Override global .main-content: fill app-body without centering */
.main-content {
  max-width: none;
  margin: 0;
  width: 100%;
  flex: 1;
}
</style>
