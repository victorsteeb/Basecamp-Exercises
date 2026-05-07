<template>
  <div class="restocking">
    <div class="page-header">
      <h2>Restocking Planner</h2>
      <p>Set your available budget and review recommended items to restock based on demand forecasts.</p>
    </div>

    <div v-if="loading" class="loading">Loading demand forecasts...</div>
    <div v-else-if="error" class="error">{{ error }}</div>
    <div v-else>
      <!-- Budget slider card -->
      <div class="card budget-card">
        <div class="card-header">
          <h3 class="card-title">Available Budget</h3>
          <span class="budget-display">${{ budget.toLocaleString() }}</span>
        </div>
        <div class="slider-container">
          <span class="slider-label">$0</span>
          <input
            type="range"
            v-model.number="budget"
            min="0"
            max="50000"
            step="500"
            class="budget-slider"
          />
          <span class="slider-label">$50,000</span>
        </div>
      </div>

      <!-- Summary stats -->
      <div class="stats-grid">
        <div class="stat-card info">
          <div class="stat-label">Items to Restock</div>
          <div class="stat-value">{{ recommendedItems.length }}</div>
        </div>
        <div class="stat-card warning">
          <div class="stat-label">Total Cost</div>
          <div class="stat-value">${{ totalCost.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }}</div>
        </div>
        <div class="stat-card success">
          <div class="stat-label">Remaining Budget</div>
          <div class="stat-value">${{ remainingBudget.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }}</div>
        </div>
      </div>

      <!-- Success/error banners -->
      <div v-if="submitSuccess" class="banner success-banner">
        Order submitted successfully! View it in the Orders tab under Submitted Orders.
      </div>
      <div v-if="submitError" class="banner error-banner">{{ submitError }}</div>

      <!-- Recommendations table -->
      <div class="card">
        <div class="card-header">
          <h3 class="card-title">Recommended Restocking Items ({{ recommendedItems.length }})</h3>
          <button
            class="btn-primary"
            :disabled="recommendedItems.length === 0 || submitting || submitSuccess"
            @click="placeOrder"
          >
            {{ submitting ? 'Placing Order...' : 'Place Order' }}
          </button>
        </div>
        <div v-if="recommendedItems.length === 0" class="empty-state">
          Increase your budget to see restocking recommendations.
        </div>
        <div v-else class="table-container">
          <table class="restock-table">
            <thead>
              <tr>
                <th>SKU</th>
                <th>Item Name</th>
                <th>Forecasted Demand</th>
                <th>Qty to Order</th>
                <th>Unit Cost</th>
                <th>Subtotal</th>
                <th>Lead Time</th>
                <th>Trend</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in recommendedItems" :key="item.id">
                <td><strong>{{ item.item_sku }}</strong></td>
                <td>{{ item.item_name }}</td>
                <td>{{ item.forecasted_demand.toLocaleString() }}</td>
                <td><strong>{{ item.forecasted_demand.toLocaleString() }}</strong></td>
                <td>${{ item.unit_cost.toFixed(2) }}</td>
                <td><strong>${{ (item.forecasted_demand * item.unit_cost).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }}</strong></td>
                <td>{{ item.lead_time_days }} days</td>
                <td><span :class="['badge', item.trend]">{{ item.trend }}</span></td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Skipped items (not enough budget) -->
      <div v-if="skippedItems.length > 0" class="card skipped-card">
        <div class="card-header">
          <h3 class="card-title">Items Exceeding Budget ({{ skippedItems.length }})</h3>
        </div>
        <div class="table-container">
          <table>
            <thead>
              <tr>
                <th>SKU</th>
                <th>Item Name</th>
                <th>Required Cost</th>
                <th>Trend</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in skippedItems" :key="item.id">
                <td><strong>{{ item.item_sku }}</strong></td>
                <td>{{ item.item_name }}</td>
                <td class="cost-exceeded">${{ (item.forecasted_demand * item.unit_cost).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }}</td>
                <td><span :class="['badge', item.trend]">{{ item.trend }}</span></td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted } from 'vue'
import { api } from '../api'

export default {
  name: 'Restocking',
  setup() {
    const loading = ref(true)
    const error = ref(null)
    const forecasts = ref([])
    const budget = ref(10000)
    const submitting = ref(false)
    const submitSuccess = ref(false)
    const submitError = ref(null)

    const loadForecasts = async () => {
      try {
        loading.value = true
        error.value = null
        forecasts.value = await api.getDemandForecasts()
      } catch (err) {
        error.value = 'Failed to load demand forecasts: ' + err.message
      } finally {
        loading.value = false
      }
    }

    // Sort by trend priority (increasing > stable > decreasing), then by forecasted_demand DESC
    const sortedForecasts = computed(() => {
      const trendPriority = { increasing: 0, stable: 1, decreasing: 2 }
      return [...forecasts.value].sort((a, b) => {
        const trendDiff = (trendPriority[a.trend] ?? 3) - (trendPriority[b.trend] ?? 3)
        if (trendDiff !== 0) return trendDiff
        return b.forecasted_demand - a.forecasted_demand
      })
    })

    // Greedy allocation: add items while budget allows
    const allocationResult = computed(() => {
      let remaining = budget.value
      const recommended = []
      const skipped = []

      for (const item of sortedForecasts.value) {
        const itemCost = item.forecasted_demand * item.unit_cost
        if (itemCost <= remaining) {
          recommended.push(item)
          remaining -= itemCost
        } else {
          skipped.push(item)
        }
      }

      return { recommended, skipped, remaining }
    })

    const recommendedItems = computed(() => allocationResult.value.recommended)
    const skippedItems = computed(() => allocationResult.value.skipped)
    const remainingBudget = computed(() => allocationResult.value.remaining)
    const totalCost = computed(() => budget.value - remainingBudget.value)

    const placeOrder = async () => {
      submitting.value = true
      submitError.value = null
      try {
        await api.submitRestockingOrder({
          budget: budget.value,
          items: recommendedItems.value.map(item => ({
            sku: item.item_sku,
            name: item.item_name,
            quantity: item.forecasted_demand,
            unit_cost: item.unit_cost,
            lead_time_days: item.lead_time_days
          }))
        })
        submitSuccess.value = true
      } catch (err) {
        submitError.value = 'Failed to submit order: ' + err.message
      } finally {
        submitting.value = false
      }
    }

    onMounted(loadForecasts)

    return {
      loading,
      error,
      budget,
      recommendedItems,
      skippedItems,
      totalCost,
      remainingBudget,
      submitting,
      submitSuccess,
      submitError,
      placeOrder
    }
  }
}
</script>

<style scoped>
.budget-card .card-header {
  align-items: center;
}

.budget-display {
  font-size: 1.75rem;
  font-weight: 700;
  color: #2563eb;
}

.slider-container {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 0.5rem 0;
}

.slider-label {
  font-size: 0.813rem;
  color: #64748b;
  font-weight: 500;
  white-space: nowrap;
}

.budget-slider {
  flex: 1;
  height: 6px;
  -webkit-appearance: none;
  appearance: none;
  border-radius: 3px;
  background: #e2e8f0;
  outline: none;
  cursor: pointer;
}

.budget-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  appearance: none;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #2563eb;
  cursor: pointer;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
}

.budget-slider::-moz-range-thumb {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #2563eb;
  cursor: pointer;
  border: none;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.2);
}

.btn-primary {
  padding: 0.625rem 1.5rem;
  background: #2563eb;
  color: white;
  border: none;
  border-radius: 6px;
  font-size: 0.938rem;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s ease;
}

.btn-primary:hover:not(:disabled) {
  background: #1d4ed8;
}

.btn-primary:disabled {
  background: #94a3b8;
  cursor: not-allowed;
}

.empty-state {
  text-align: center;
  padding: 3rem;
  color: #64748b;
  font-size: 0.938rem;
}

.banner {
  padding: 1rem 1.25rem;
  border-radius: 8px;
  margin-bottom: 1.25rem;
  font-size: 0.938rem;
  font-weight: 500;
}

.success-banner {
  background: #d1fae5;
  color: #065f46;
  border: 1px solid #6ee7b7;
}

.error-banner {
  background: #fef2f2;
  color: #991b1b;
  border: 1px solid #fecaca;
}

.skipped-card {
  opacity: 0.7;
}

.cost-exceeded {
  color: #dc2626;
  font-weight: 600;
}

.restock-table {
  table-layout: fixed;
  width: 100%;
}
</style>
