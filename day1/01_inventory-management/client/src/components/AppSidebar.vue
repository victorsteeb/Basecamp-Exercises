<template>
  <aside class="app-sidebar" aria-label="Primary navigation">
    <div class="sidebar-brand">
      <h1 class="brand-title">{{ brandTitle }}</h1>
      <span v-if="brandSubtitle" class="brand-subtitle">{{ brandSubtitle }}</span>
    </div>

    <nav class="sidebar-nav" aria-label="Main">
      <router-link
        v-for="link in links"
        :key="link.to"
        :to="link.to"
        class="sidebar-link"
        :active-class="link.to === '/' ? '' : 'is-active'"
        :exact-active-class="link.to === '/' ? 'is-active' : ''"
      >
        <span class="sidebar-icon" aria-hidden="true" v-html="link.icon"></span>
        <span class="sidebar-label">{{ link.label }}</span>
      </router-link>
    </nav>

    <div class="sidebar-footer">
      <slot name="language" />
      <slot name="profile" />
    </div>
  </aside>
</template>

<script>
export default {
  name: 'AppSidebar',
  props: {
    brandTitle:    { type: String, required: true },
    brandSubtitle: { type: String, default: '' },
    links: { type: Array, required: true }
  }
}
</script>

<style scoped>
.app-sidebar {
  position: fixed;
  top: 0;
  left: 0;
  bottom: 0;
  width: 240px;
  background: #0f172a;
  color: #cbd5e1;
  display: flex;
  flex-direction: column;
  border-right: 1px solid #1e293b;
  z-index: 100;
  overflow: hidden;
}

.sidebar-brand {
  padding: 1.375rem 1.5rem 1.25rem;
  border-bottom: 1px solid #1e293b;
  flex-shrink: 0;
}

.brand-title {
  font-size: 1.0625rem;
  font-weight: 700;
  color: #ffffff;
  letter-spacing: -0.02em;
  margin: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.brand-subtitle {
  display: block;
  font-size: 0.6875rem;
  color: #64748b;
  margin-top: 0.25rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.sidebar-nav {
  flex: 1;
  padding: 0.875rem 0.75rem;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
}

.sidebar-link {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.5625rem 0.875rem;
  border-radius: 7px;
  color: #cbd5e1;
  text-decoration: none;
  font-size: 0.875rem;
  font-weight: 500;
  transition: background 150ms ease, color 150ms ease;
  white-space: nowrap;
}

.sidebar-link:hover {
  background: #1e293b;
  color: #ffffff;
}

.sidebar-link.is-active {
  background: #2563eb;
  color: #ffffff;
}

.sidebar-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 18px;
  height: 18px;
  flex-shrink: 0;
  opacity: 0.9;
}

.sidebar-icon :deep(svg) {
  width: 18px;
  height: 18px;
}

.sidebar-label {
  overflow: hidden;
  text-overflow: ellipsis;
}

.sidebar-footer {
  padding: 0.875rem 1rem;
  border-top: 1px solid #1e293b;
  display: flex;
  flex-direction: column;
  gap: 0.625rem;
  flex-shrink: 0;
}
</style>
