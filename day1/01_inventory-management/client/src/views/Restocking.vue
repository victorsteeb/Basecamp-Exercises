<template>
  <div class="restocking">
    <div class="page-header">
      <h2>Restocking</h2>
      <p>Set your available budget to get restocking recommendations based on demand forecasts.</p>
    </div>

    <!-- Budget card -->
    <div class="card budget-card">
      <div class="budget-label">Available Budget</div>
      <div class="budget-display">{{ formatCurrency(budget) }}</div>
      <input
        type="range"
        min="0"
        max="200000"
        step="1000"
        v-model.number="budget"
        class="budget-slider"
      />
      <div class="budget-stats">
        <div class="stat-chip">
          <span class="chip-label">Total Cost</span>
          <span class="chip-value">{{ formatCurrency(recommendations.total_cost) }}</span>
        </div>
        <div class="stat-chip">
          <span class="chip-label">Items Recommended</span>
          <span class="chip-value">{{ recommendations.items.length }}</span>
        </div>
        <div class="stat-chip">
          <span class="chip-label">Remaining Budget</span>
          <span class="chip-value">{{ formatCurrency(recommendations.remaining_budget) }}</span>
        </div>
      </div>
    </div>

    <!-- Success banner -->
    <div v-if="orderPlaced" class="success-banner">
      <div class="success-content">
        <span>Order {{ placedOrderNumber }} placed successfully. Expected delivery in 14 days.</span>
        <button class="dismiss-btn" @click="dismissSuccess">Dismiss</button>
      </div>
    </div>

    <div v-if="loading" class="loading">Loading recommendations...</div>
    <div v-else-if="error" class="error">{{ error }}</div>
    <div v-else>
      <!-- Recommendations table -->
      <div class="card">
        <div class="card-header">
          <h3 class="card-title">Recommended Items</h3>
          <span class="badge info">{{ recommendations.items.length }}</span>
        </div>
        <div class="table-container">
          <table v-if="recommendations.items.length > 0">
            <thead>
              <tr>
                <th>Item Name</th>
                <th>SKU</th>
                <th>Trend</th>
                <th>Current Demand</th>
                <th>Forecasted</th>
                <th>Restock Qty</th>
                <th>Unit Cost</th>
                <th>Line Total</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="item in recommendations.items" :key="item.item_sku">
                <td>{{ item.item_name }}</td>
                <td><code class="sku">{{ item.item_sku }}</code></td>
                <td>
                  <!-- trend value is lowercase from API -->
                  <span :class="['badge', item.trend]">{{ item.trend }}</span>
                </td>
                <td>{{ item.current_demand }}</td>
                <td>{{ item.forecasted_demand }}</td>
                <td>{{ item.restock_quantity }}</td>
                <td>{{ formatCurrency(item.unit_cost) }}</td>
                <td><strong>{{ formatCurrency(item.line_total) }}</strong></td>
              </tr>
            </tbody>
            <tfoot>
              <tr class="total-row">
                <td colspan="7" class="total-label">Total Cost</td>
                <td><strong>{{ formatCurrency(recommendations.total_cost) }}</strong></td>
              </tr>
            </tfoot>
          </table>
          <!-- Empty state when budget is too low to cover any item -->
          <div v-else class="empty-state">
            Increase your budget to include more items.
          </div>
        </div>
      </div>

      <!-- Place Order button -->
      <div class="place-order-row">
        <button
          class="btn-primary"
          :disabled="recommendations.items.length === 0 || orderPlaced"
          @click="placeOrder"
        >
          Place Order
        </button>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, watch, onMounted } from 'vue'
import { api } from '../api'

export default {
  name: 'Restocking',
  setup() {
    const budget = ref(50000)
    const loading = ref(false)
    const error = ref(null)
    const orderPlaced = ref(false)
    const placedOrderNumber = ref(null)

    // Default shape avoids null-guard checks in the template
    const recommendations = ref({
      items: [],
      total_cost: 0,
      budget: 50000,
      remaining_budget: 50000
    })

    const formatCurrency = (value) => {
      if (value == null) return '$0'
      return value.toLocaleString('en-US', { style: 'currency', currency: 'USD' })
    }

    const loadRecommendations = async () => {
      loading.value = true
      error.value = null
      try {
        const data = await api.getRestockingRecommendations(budget.value)
        recommendations.value = data
      } catch (err) {
        error.value = 'Failed to load recommendations'
        console.error(err)
      } finally {
        loading.value = false
      }
    }

    // Manual 300ms debounce — avoids @vueuse/core dependency
    let debounceTimer = null
    watch(budget, () => {
      clearTimeout(debounceTimer)
      debounceTimer = setTimeout(() => {
        loadRecommendations()
      }, 300)
    })

    const placeOrder = async () => {
      const mappedItems = recommendations.value.items.map(i => ({
        sku: i.item_sku,
        name: i.item_name,
        quantity: i.restock_quantity,
        unit_price: i.unit_cost
      }))

      try {
        const result = await api.submitRestockingOrder({
          items: mappedItems,
          customer: 'Internal Restocking'
        })
        placedOrderNumber.value = result.order_number
        orderPlaced.value = true
      } catch (err) {
        error.value = 'Failed to place order'
        console.error(err)
      }
    }

    const dismissSuccess = () => {
      // Reset so the user can place another order after reviewing
      orderPlaced.value = false
      placedOrderNumber.value = null
    }

    onMounted(() => loadRecommendations())

    return {
      budget,
      loading,
      error,
      recommendations,
      orderPlaced,
      placedOrderNumber,
      formatCurrency,
      placeOrder,
      dismissSuccess
    }
  }
}
</script>

<style scoped>
.restocking {
  padding: 0;
}

/* Budget card */
.budget-card {
  margin-bottom: 1.25rem;
}

.budget-label {
  font-size: 0.875rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: #64748b;
  margin-bottom: 0.5rem;
}

.budget-display {
  font-size: 2.5rem;
  font-weight: 700;
  color: #0f172a;
  letter-spacing: -0.025em;
  margin-bottom: 1rem;
}

.budget-slider {
  width: 100%;
  accent-color: #2563eb;
  margin-bottom: 1.25rem;
  cursor: pointer;
}

.budget-stats {
  display: flex;
  gap: 1rem;
  flex-wrap: wrap;
}

.stat-chip {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 0.625rem 1rem;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  min-width: 160px;
}

.chip-label {
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: #64748b;
}

.chip-value {
  font-size: 1.125rem;
  font-weight: 700;
  color: #0f172a;
}

/* Success banner */
.success-banner {
  background: #d1fae5;
  border: 1px solid #6ee7b7;
  border-radius: 10px;
  padding: 1rem 1.25rem;
  margin-bottom: 1.25rem;
}

.success-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  color: #065f46;
  font-weight: 500;
}

.dismiss-btn {
  background: transparent;
  border: 1px solid #059669;
  color: #065f46;
  padding: 0.375rem 0.875rem;
  border-radius: 6px;
  font-size: 0.813rem;
  font-weight: 600;
  cursor: pointer;
  white-space: nowrap;
  transition: background 0.15s;
}

.dismiss-btn:hover {
  background: #a7f3d0;
}

/* Table footer total row */
.total-row td {
  border-top: 2px solid #e2e8f0;
  font-size: 0.875rem;
  padding-top: 0.75rem;
  padding-bottom: 0.75rem;
}

.total-label {
  text-align: right;
  font-weight: 600;
  color: #475569;
  text-transform: uppercase;
  letter-spacing: 0.025em;
  font-size: 0.75rem;
}

/* SKU code style */
.sku {
  font-family: 'SFMono-Regular', Consolas, monospace;
  font-size: 0.813rem;
  background: #f1f5f9;
  padding: 0.125rem 0.375rem;
  border-radius: 4px;
  color: #334155;
}

/* Empty state */
.empty-state {
  padding: 2rem;
  text-align: center;
  color: #64748b;
  font-size: 0.938rem;
}

/* Place Order row */
.place-order-row {
  display: flex;
  justify-content: flex-end;
  margin-top: 0.5rem;
  margin-bottom: 1.5rem;
}

.btn-primary {
  background: #2563eb;
  color: white;
  border: none;
  padding: 0.625rem 1.5rem;
  border-radius: 8px;
  font-size: 0.938rem;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.15s;
}

.btn-primary:hover:not(:disabled) {
  background: #1d4ed8;
}

.btn-primary:disabled {
  background: #94a3b8;
  cursor: not-allowed;
}
</style>
