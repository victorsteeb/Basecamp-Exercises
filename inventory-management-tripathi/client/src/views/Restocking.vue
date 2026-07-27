<template>
  <div class="restocking">
    <div class="page-header">
      <h2>Restocking Planner</h2>
      <p>Select a budget and we'll recommend items to restock based on demand forecasts.</p>
    </div>

    <div v-if="loading" class="loading">Loading...</div>
    <div v-else-if="error" class="error">{{ error }}</div>
    <div v-else>
      <!-- Budget Slider Card -->
      <div class="card">
        <div class="card-header">
          <h3 class="card-title">Available Budget</h3>
          <span class="budget-display">${{ budget.toLocaleString() }}</span>
        </div>
        <div class="slider-wrapper">
          <input
            type="range"
            min="10000"
            max="500000"
            step="1000"
            v-model.number="budget"
            class="budget-slider"
          />
          <div class="slider-bounds">
            <span>Min: $10,000</span>
            <span>Max: $500,000</span>
          </div>
        </div>
        <div class="budget-summary">
          <span class="summary-item">
            Total Selected: <strong>${{ totalSelected.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }}</strong>
          </span>
          <span :class="['summary-item', 'remaining', remaining >= 0 ? 'positive' : 'negative']">
            Remaining: <strong>${{ remaining.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }}</strong>
          </span>
        </div>
      </div>

      <!-- Recommended Items Card -->
      <div class="card">
        <div class="card-header">
          <h3 class="card-title">Recommended Items</h3>
        </div>
        <div class="table-container">
          <table>
            <thead>
              <tr>
                <th>Item</th>
                <th>SKU</th>
                <th>Trend</th>
                <th>Qty to Order</th>
                <th>Unit Cost</th>
                <th>Total Cost</th>
                <th>Select</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="recommendedItems.length === 0">
                <td colspan="7" class="no-data">No demand forecast data matches current filters.</td>
              </tr>
              <tr v-for="item in recommendedItems" :key="item.sku">
                <td>{{ item.item_name }}</td>
                <td><code class="sku-code">{{ item.sku }}</code></td>
                <td><span :class="['badge', item.trend]">{{ item.trend }}</span></td>
                <td>{{ item.quantity.toLocaleString() }}</td>
                <td>${{ item.unit_cost.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }}</td>
                <td>${{ item.total_cost.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }}</td>
                <td>
                  <input
                    type="checkbox"
                    :checked="selectedSkus.has(item.sku)"
                    @change="toggleItem(item)"
                    class="item-checkbox"
                  />
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Feedback banners -->
      <div v-if="successMessage" class="success-banner">{{ successMessage }}</div>
      <div v-if="submitError" class="error">{{ submitError }}</div>

      <!-- Place Order -->
      <div class="place-order-row">
        <button
          class="place-order-btn"
          :disabled="selectedSkus.size === 0 || totalSelected > budget || submitting"
          @click="placeOrder"
        >
          {{ submitting ? 'Submitting...' : 'Place Order' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, watch, onMounted } from 'vue'
import { api } from '../api'
import { useFilters } from '../composables/useFilters'

export default {
  name: 'Restocking',
  emits: ['order-placed'],
  setup(props, { emit }) {
    const { selectedLocation, selectedCategory, getCurrentFilters } = useFilters()

    const budget = ref(50000)
    const forecasts = ref([])
    const inventoryItems = ref([])
    const loading = ref(false)
    const error = ref(null)
    const submitting = ref(false)
    const successMessage = ref(null)
    const submitError = ref(null)
    // Use a new Set each assignment to ensure reactivity
    const selectedSkus = ref(new Set())

    const inventoryMap = computed(() => {
      const map = {}
      for (const item of inventoryItems.value) {
        map[item.sku] = item
      }
      return map
    })

    const getLeadTimeDays = (unitCost) => {
      if (unitCost < 100) return 7
      if (unitCost < 500) return 14
      return 21
    }

    const recommendedItems = computed(() => {
      const items = []
      for (const forecast of forecasts.value) {
        const inv = inventoryMap.value[forecast.item_sku]
        if (!inv) continue
        const unit_cost = inv.unit_cost
        const quantity = forecast.forecasted_demand
        const total_cost = quantity * unit_cost
        const lead_time_days = getLeadTimeDays(unit_cost)
        items.push({
          sku: forecast.item_sku,
          item_name: forecast.item_name,
          trend: forecast.trend,
          quantity,
          unit_cost,
          total_cost,
          lead_time_days
        })
      }
      // Sort: increasing trend first, then by forecasted_demand descending
      const trendOrder = { increasing: 0, stable: 1, decreasing: 2 }
      items.sort((a, b) => {
        const tA = trendOrder[a.trend] ?? 3
        const tB = trendOrder[b.trend] ?? 3
        if (tA !== tB) return tA - tB
        return b.quantity - a.quantity
      })
      return items
    })

    const autoSelect = () => {
      const newSelected = new Set()
      let running = 0
      for (const item of recommendedItems.value) {
        if (running + item.total_cost <= budget.value) {
          newSelected.add(item.sku)
          running += item.total_cost
        }
      }
      selectedSkus.value = newSelected
    }

    const totalSelected = computed(() => {
      let total = 0
      // Access selectedSkus.value so Vue tracks the ref
      const skus = selectedSkus.value
      for (const item of recommendedItems.value) {
        if (skus.has(item.sku)) {
          total += item.total_cost
        }
      }
      return total
    })

    const remaining = computed(() => budget.value - totalSelected.value)

    const toggleItem = (item) => {
      const newSet = new Set(selectedSkus.value)
      if (newSet.has(item.sku)) {
        newSet.delete(item.sku)
      } else {
        newSet.add(item.sku)
      }
      selectedSkus.value = newSet
    }

    const loadData = async () => {
      loading.value = true
      error.value = null
      try {
        const [forecastData, inventoryData] = await Promise.all([
          api.getDemandForecasts(),
          api.getInventory(getCurrentFilters())
        ])
        forecasts.value = forecastData
        inventoryItems.value = inventoryData
        autoSelect()
      } catch (err) {
        error.value = 'Failed to load data'
        console.error(err)
      } finally {
        loading.value = false
      }
    }

    watch([selectedLocation, selectedCategory], () => {
      loadData()
    })

    watch(budget, () => {
      autoSelect()
    })

    const placeOrder = async () => {
      if (selectedSkus.value.size === 0 || totalSelected.value > budget.value) return
      submitting.value = true
      successMessage.value = null
      submitError.value = null
      try {
        const items = recommendedItems.value
          .filter(item => selectedSkus.value.has(item.sku))
          .map(item => ({
            sku: item.sku,
            name: item.item_name,
            quantity: item.quantity,
            unit_cost: item.unit_cost,
            total_cost: item.total_cost,
            lead_time_days: item.lead_time_days
          }))
        const warehouse =
          selectedLocation.value === 'all' ? 'All Warehouses' : selectedLocation.value
        const result = await api.createRestockingOrder({
          items,
          budget: budget.value,
          warehouse
        })
        successMessage.value = `Order submitted successfully! Order ID: ${result.id}`
        emit('order-placed', result)
      } catch (err) {
        submitError.value = 'Failed to place order. Please try again.'
        console.error(err)
      } finally {
        submitting.value = false
      }
    }

    onMounted(loadData)

    return {
      budget,
      loading,
      error,
      submitting,
      successMessage,
      submitError,
      selectedSkus,
      recommendedItems,
      totalSelected,
      remaining,
      toggleItem,
      placeOrder
    }
  }
}
</script>

<style scoped>
.restocking {
  padding: 0;
}

.budget-display {
  font-size: 1.5rem;
  font-weight: 700;
  color: #2563eb;
  letter-spacing: -0.025em;
}

.slider-wrapper {
  padding: 0.75rem 0 1rem;
}

.budget-slider {
  width: 100%;
  height: 6px;
  border-radius: 3px;
  outline: none;
  cursor: pointer;
  accent-color: #2563eb;
  margin-bottom: 0.5rem;
  display: block;
}

.slider-bounds {
  display: flex;
  justify-content: space-between;
  font-size: 0.813rem;
  color: #64748b;
}

.budget-summary {
  display: flex;
  gap: 2rem;
  padding-top: 0.875rem;
  border-top: 1px solid #e2e8f0;
}

.summary-item {
  font-size: 0.938rem;
  color: #334155;
}

.remaining.positive strong {
  color: #059669;
}

.remaining.negative strong {
  color: #dc2626;
}

.no-data {
  text-align: center;
  color: #64748b;
  padding: 2.5rem;
  font-size: 0.938rem;
}

.sku-code {
  font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
  font-size: 0.813rem;
  color: #475569;
  background: #f1f5f9;
  padding: 0.125rem 0.375rem;
  border-radius: 4px;
}

.item-checkbox {
  width: 16px;
  height: 16px;
  cursor: pointer;
  accent-color: #2563eb;
}

.success-banner {
  background: #d1fae5;
  border: 1px solid #6ee7b7;
  color: #065f46;
  padding: 0.875rem 1.25rem;
  border-radius: 8px;
  margin-bottom: 1rem;
  font-size: 0.938rem;
  font-weight: 500;
}

.place-order-row {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 1.5rem;
}

.place-order-btn {
  padding: 0.75rem 2rem;
  background: #2563eb;
  color: white;
  border: none;
  border-radius: 8px;
  font-size: 0.938rem;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s ease;
  letter-spacing: 0.01em;
}

.place-order-btn:hover:not(:disabled) {
  background: #1d4ed8;
}

.place-order-btn:disabled {
  background: #94a3b8;
  cursor: not-allowed;
}
</style>
