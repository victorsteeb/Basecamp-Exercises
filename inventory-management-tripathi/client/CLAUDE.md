# CLAUDE.md - Client

This file provides guidance to Claude Code (claude.ai/code) when working with the Vue 3 frontend.

## Running the Client

```bash
# From client directory
npm run dev
# Runs on http://localhost:3000
```

## Development Best Practices

### Vue 3 Composition API Patterns

**Component Structure:**
```vue
<template>
  <!-- Template: Keep clean and declarative -->
</template>

<script>
import { ref, computed, watch, onMounted } from 'vue'

export default {
  name: 'ComponentName',
  props: {
    // Define props with types and defaults
  },
  setup(props) {
    // Reactive state
    const data = ref([])
    const loading = ref(false)

    // Computed properties
    const filteredData = computed(() => {
      return data.value.filter(/* logic */)
    })

    // Methods
    const loadData = async () => {
      // Implementation
    }

    // Lifecycle
    onMounted(() => {
      loadData()
    })

    // Return everything used in template
    return {
      data,
      loading,
      filteredData,
      loadData
    }
  }
}
</script>

<style scoped>
  /* Scoped styles */
</style>
```

**Why Composition API:**
- Better code organization by feature
- Easier to extract and reuse logic
- TypeScript support
- Smaller bundle size
- More flexible than Options API

### Reactive Data Best Practices

**refs vs computed:**
- Use `ref()` for values that change via assignment
- Use `computed()` for values derived from other reactive data
- computed properties are cached until dependencies change
- Never mutate computed properties

**Example:**
```javascript
// refs - mutable state
const searchQuery = ref('')
const items = ref([])

// computed - derived from refs
const filteredItems = computed(() => {
  if (!searchQuery.value) return items.value
  return items.value.filter(item =>
    item.name.toLowerCase().includes(searchQuery.value.toLowerCase())
  )
})
```

**Accessing ref values:**
- In `<script>`: Use `.value` (e.g., `count.value++`)
- In `<template>`: No `.value` needed (automatic unwrapping)

### Data Loading Pattern

**Standard Approach:**
```javascript
const loading = ref(true)
const error = ref(null)
const data = ref([])

const loadData = async () => {
  try {
    loading.value = true
    error.value = null
    data.value = await api.getData(filters)
  } catch (err) {
    error.value = 'Failed to load data'
    console.error('Load error:', err)
  } finally {
    loading.value = false
  }
}
```

**Display states in template:**
```vue
<div v-if="loading">Loading...</div>
<div v-else-if="error">{{ error }}</div>
<div v-else>
  <!-- Show data -->
</div>
```

### Filter Management with Composables

**Pattern:**
1. Create composable for shared state
2. Export refs for UI binding
3. Provide helper functions
4. Watch for changes to trigger effects

**Example composable:**
```javascript
// composables/useFilters.js
import { ref, computed } from 'vue'

const selectedCategory = ref('all')
const selectedWarehouse = ref('all')

export function useFilters() {
  const hasActiveFilters = computed(() => {
    return selectedCategory.value !== 'all' ||
           selectedWarehouse.value !== 'all'
  })

  const resetFilters = () => {
    selectedCategory.value = 'all'
    selectedWarehouse.value = 'all'
  }

  const getCurrentFilters = () => {
    return {
      category: selectedCategory.value,
      warehouse: selectedWarehouse.value
    }
  }

  return {
    selectedCategory,
    selectedWarehouse,
    hasActiveFilters,
    resetFilters,
    getCurrentFilters
  }
}
```

### Reactivity Best Practices

**v-for keys:**
```vue
<!-- ❌ Bad - using index -->
<div v-for="(item, index) in items" :key="index">

<!-- ✅ Good - using unique ID -->
<div v-for="item in items" :key="item.id">
```

**Why:** Using index as key causes Vue to reuse DOM elements incorrectly when list changes.

**Prop mutation:**
```javascript
// ❌ Bad - mutating props
props.user.name = 'New Name'

// ✅ Good - emit event to parent
emit('update:user', { ...props.user, name: 'New Name' })
```

**Date handling:**
```javascript
// ❌ Bad - no validation
const month = new Date(order.date).getMonth()

// ✅ Good - validate first
const date = new Date(order.date)
if (!isNaN(date.getTime())) {
  const month = date.getMonth()
}
```

### Component Communication

**Props Down, Events Up:**
```javascript
// Parent component
<ChildComponent
  :data="items"
  @update="handleUpdate"
/>

// Child component
props: {
  data: {
    type: Array,
    required: true
  }
},
setup(props, { emit }) {
  const update = () => {
    emit('update', newValue)
  }
}
```

**When to use composables:**
- State shared across multiple components
- Logic used in multiple places
- Authentication state
- Global filters
- Theme/settings

### Chart Implementation Best Practices

**Use computed properties:**
```javascript
const chartData = computed(() => {
  // Transform raw data for chart
  return rawData.value.map(item => ({
    label: item.month,
    value: item.total
  }))
})
```

**SVG charts:**
- Define viewBox for responsive scaling
- Use percentages for positioning when possible
- Handle empty data gracefully
- Add ARIA labels for accessibility

**Performance:**
- Keep chart calculations in computed properties
- Avoid recalculating on every render
- Use v-show instead of v-if for frequently toggled charts
- Debounce resize handlers

### Styling Best Practices

**Scoped styles:**
```vue
<style scoped>
/* Only affects this component */
.card { }
</style>
```

**Use CSS variables for themes:**
```css
:root {
  --primary-color: #3b82f6;
  --danger-color: #ef4444;
}

.button {
  background: var(--primary-color);
}
```

**Responsive design:**
- Use rem/em units for scalability
- Mobile-first approach
- CSS Grid for layouts
- Flexbox for component arrangement

**Class binding:**
```vue
<div :class="['card', { 'card-active': isActive }]">
<div :class="{ danger: hasError, success: isComplete }">
```

### Performance Considerations

**Computed vs Methods:**
- Computed: Cached until dependencies change (use for calculations)
- Methods: Run every time accessed (use for actions)

**v-show vs v-if:**
- v-show: Toggles CSS display (better for frequent toggles)
- v-if: Adds/removes from DOM (better for rarely shown content)

**Lazy loading:**
```javascript
// Dynamic import for code splitting
const HeavyComponent = defineAsyncComponent(() =>
  import('./components/HeavyComponent.vue')
)
```

**Watch with debounce:**
```javascript
import { watchDebounced } from '@vueuse/core'

watchDebounced(
  searchQuery,
  (newValue) => {
    // API call here
  },
  { debounce: 500 }
)
```

### Common Pitfalls

**Avoid:**
- ❌ Using array index as v-for key
- ❌ Mutating props directly
- ❌ Forgetting to validate dates before parsing
- ❌ Heavy computations in methods instead of computed
- ❌ Not handling loading/error states
- ❌ Mixing Composition API and Options API in same component

**Do:**
- ✅ Use unique IDs for keys
- ✅ Emit events to update parent data
- ✅ Validate all external data
- ✅ Use computed properties for derived data
- ✅ Always show loading and error states
- ✅ Stick to Composition API throughout project

### API Integration

**Centralize API calls:**
```javascript
// api.js
import axios from 'axios'

const API_BASE = 'http://localhost:8001/api'

export const api = {
  async getItems(filters) {
    const params = new URLSearchParams()
    if (filters.category !== 'all') {
      params.append('category', filters.category)
    }
    const response = await axios.get(`${API_BASE}/items?${params}`)
    return response.data
  }
}
```

**Use in component:**
```javascript
import { api } from '@/api'

const loadItems = async () => {
  const filters = getCurrentFilters()
  items.value = await api.getItems(filters)
}
```

### Number Formatting

**Currency:**
```javascript
const formatted = value.toLocaleString('en-US', {
  style: 'currency',
  currency: 'USD'
})
// Output: $1,234.56
```

**Large numbers:**
```javascript
const formatted = value.toLocaleString()
// Output: 1,234,567
```

**Percentages:**
```javascript
const formatted = (value * 100).toFixed(1) + '%'
// Output: 45.2%
```

### Testing Components

**What to test:**
- Component renders correctly
- Props are handled properly
- Events are emitted correctly
- Computed properties calculate correctly
- User interactions work as expected

**Example:**
```javascript
import { mount } from '@vue/test-utils'
import MyComponent from './MyComponent.vue'

describe('MyComponent', () => {
  it('displays data correctly', () => {
    const wrapper = mount(MyComponent, {
      props: { items: mockItems }
    })
    expect(wrapper.text()).toContain('Expected text')
  })
})
```

### Debugging

**Vue DevTools:**
- Install Vue DevTools browser extension
- Inspect component hierarchy
- View reactive state in real-time
- Track events and performance

**Console logging:**
```javascript
// In setup()
console.log('Data:', data.value)

// Watch for changes
watch(data, (newVal) => {
  console.log('Data changed:', newVal)
})
```

**Common issues:**
- Reactivity not working → Forgot `.value` in script
- Computed not updating → Dependency not reactive
- Props not reactive → Destructured props in setup
- v-for not updating → Using wrong key

### Code Organization

**When to extract component:**
- Template is >100 lines
- Logic is >150 lines
- Component is reused in multiple places
- Component has distinct responsibility

**When to create composable:**
- State shared across components
- Reusable logic pattern
- Complex logic that can be isolated
- API interaction patterns

**File structure:**
```
src/
├── views/           # Page-level components
├── components/      # Reusable UI components
├── composables/     # Shared logic
├── api.js          # API client
└── main.js         # App entry
```

## Quick Reference

**Start dev server:** `npm run dev`
**Build for production:** `npm run build`
**Component structure:** Template → Script (Composition API) → Scoped Styles
**Data loading:** loading state → try/catch → finally
**Filters:** Composable → refs → watch for changes
**Keys:** Always use unique IDs, never array index
**API calls:** Centralize in api.js, wrap in try/catch
