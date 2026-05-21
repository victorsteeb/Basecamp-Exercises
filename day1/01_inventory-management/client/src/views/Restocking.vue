<template>
  <div class="restocking">
    <div class="page-header">
      <h2>Restocking Planner</h2>
      <p>Allocate your budget across forecasted demand and submit an internal restocking order.</p>
    </div>

    <div v-if="loading" class="loading">Loading...</div>
    <div v-else-if="error" class="error">{{ error }}</div>
    <div v-else>

      <!-- Budget card -->
      <div class="card">
        <div class="card-header">
          <h3 class="card-title">Budget Allocation</h3>
        </div>

        <div class="budget-row">
          <span class="budget-label">Available Budget</span>
          <span class="budget-value">{{ currencySymbol }}{{ budget.toLocaleString() }}</span>
        </div>

        <input
          type="range"
          class="budget-slider"
          v-model.number="budget"
          :min="0"
          :max="maxBudget"
          :step="100"
        />

        <div class="slider-bounds">
          <span>{{ currencySymbol }}0</span>
          <span>{{ currencySymbol }}{{ maxBudget.toLocaleString() }}</span>
        </div>

        <div class="stats-grid">
          <div class="stat-card">
            <div class="stat-label">Items to Order</div>
            <div class="stat-value">{{ itemsToOrderCount }}</div>
          </div>
          <div class="stat-card">
            <div class="stat-label">Total Cost</div>
            <div class="stat-value" style="color: #059669;">{{ currencySymbol }}{{ totalCost.toLocaleString() }}</div>
          </div>
          <div class="stat-card">
            <div class="stat-label">Remaining Budget</div>
            <div class="stat-value" style="color: #2563eb;">{{ currencySymbol }}{{ remainingBudget.toLocaleString() }}</div>
          </div>
        </div>
      </div>

      <!-- Warehouse selector card -->
      <div class="card">
        <div class="card-header">
          <h3 class="card-title">Destination Warehouse</h3>
        </div>
        <div>
          <label class="warehouse-label">Select destination warehouse for the restocking order</label>
          <select v-model="selectedWarehouse" class="warehouse-select">
            <option value="San Francisco">San Francisco</option>
            <option value="London">London</option>
            <option value="Tokyo">Tokyo</option>
          </select>
        </div>
      </div>

      <!-- Recommendations table card -->
      <div class="card">
        <div class="card-header">
          <div>
            <h3 class="card-title">Demand-Based Recommendations</h3>
            <span class="card-subtitle">Budget allocated proportionally by forecasted demand</span>
          </div>
        </div>
        <div class="table-container">
          <table>
            <thead>
              <tr>
                <th>Item</th>
                <th>SKU</th>
                <th>Forecasted Demand</th>
                <th>Allocated Qty</th>
                <th>Unit Cost</th>
                <th>Total Cost</th>
                <th>Trend</th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="item in enrichedForecasts"
                :key="item.item_sku"
                :class="{ 'row-zeroed': item.allocatedQty === 0 }"
              >
                <td>{{ item.item_name }}</td>
                <td><strong>{{ item.item_sku }}</strong></td>
                <td>{{ item.forecasted_demand }}</td>
                <td>
                  <span v-if="item.allocatedQty > 0">{{ item.allocatedQty }}</span>
                  <span v-else class="dash">&#8212;</span>
                </td>
                <td>{{ currencySymbol }}{{ item.unit_cost.toFixed(2) }}</td>
                <td>
                  <span v-if="item.allocatedQty > 0">{{ currencySymbol }}{{ item.itemCost.toLocaleString() }}</span>
                  <span v-else class="dash">&#8212;</span>
                </td>
                <td>
                  <span :class="['badge', item.trend]">{{ item.trend }}</span>
                </td>
              </tr>
            </tbody>
            <tfoot>
              <tr class="tfoot-row">
                <td colspan="5" class="tfoot-label">Total</td>
                <td class="tfoot-total">{{ currencySymbol }}{{ totalCost.toLocaleString() }}</td>
                <td></td>
              </tr>
            </tfoot>
          </table>
        </div>
      </div>

      <!-- Submit error -->
      <div v-if="submitError" class="error">{{ submitError }}</div>

      <!-- Success banner -->
      <div v-if="submittedOrder" class="success-banner">
        <svg class="check-icon" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
          <circle cx="12" cy="12" r="12" fill="#10b981"/>
          <path d="M7 12.5l3.5 3.5 6.5-7" stroke="white" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
        </svg>
        <div>
          <div class="success-title">Order Submitted</div>
          <div class="success-detail">
            Order {{ submittedOrder.id }} has been placed for {{ submittedOrder.warehouse }}.
          </div>
          <div class="success-detail">
            Expected delivery: {{ formatDeliveryDate(submittedOrder.expected_delivery) }}
          </div>
          <router-link to="/orders" class="orders-link">View in Orders tab &rarr;</router-link>
        </div>
      </div>

      <!-- Place order button -->
      <div v-else class="action-row">
        <button
          class="place-order-btn"
          :disabled="itemsToOrderCount === 0 || submitting"
          :class="{ 'btn-disabled': itemsToOrderCount === 0 || submitting }"
          @click="placeOrder"
        >
          {{ submitting ? 'Placing Order...' : 'Place Restocking Order' }}
        </button>
      </div>

    </div>
  </div>
</template>

<script>
import { ref, computed, onMounted } from 'vue'
import { api } from '../api'
import { useI18n } from '../composables/useI18n'

export default {
  name: 'Restocking',
  setup() {
    const { currentCurrency } = useI18n()

    const loading = ref(true)
    const error = ref(null)
    const forecasts = ref([])

    const budget = ref(0)
    const selectedWarehouse = ref('San Francisco')

    const submitting = ref(false)
    const submittedOrder = ref(null)
    const submitError = ref(null)

    // Currency symbol based on locale
    const currencySymbol = computed(() => currentCurrency.value === 'JPY' ? '¥' : '$')

    // Sum of all forecasted_demand values
    const totalForecastedDemand = computed(() =>
      forecasts.value.reduce((sum, item) => sum + item.forecasted_demand, 0)
    )

    // Maximum budget = cost to fully restock everything
    const maxBudget = computed(() =>
      forecasts.value.reduce((sum, item) => sum + item.forecasted_demand * item.unit_cost, 0)
    )

    // Per-item allocation enriched with computed qty and cost, then sorted
    const enrichedForecasts = computed(() => {
      const total = totalForecastedDemand.value

      const enriched = forecasts.value.map(item => {
        // Avoid division by zero when no demand data
        const proportion = total > 0 ? item.forecasted_demand / total : 0
        const allocatedQty = Math.floor(budget.value * proportion / item.unit_cost)
        const itemCost = allocatedQty * item.unit_cost
        return { ...item, allocatedQty, itemCost }
      })

      // Items with allocation first (sorted by itemCost desc), then zero-qty items
      const withQty = enriched.filter(i => i.allocatedQty > 0).sort((a, b) => b.itemCost - a.itemCost)
      const withoutQty = enriched.filter(i => i.allocatedQty === 0)
      return [...withQty, ...withoutQty]
    })

    const totalCost = computed(() =>
      enrichedForecasts.value.reduce((sum, item) => sum + item.itemCost, 0)
    )

    const remainingBudget = computed(() => budget.value - totalCost.value)

    const itemsToOrderCount = computed(() =>
      enrichedForecasts.value.filter(i => i.allocatedQty > 0).length
    )

    const loadForecasts = async () => {
      loading.value = true
      error.value = null
      try {
        const data = await api.getDemandForecasts()
        forecasts.value = data
        // Set budget default to half of max after data loads, guarding against empty data
        if (maxBudget.value > 0) {
          budget.value = Math.floor(maxBudget.value / 2)
        }
      } catch (err) {
        error.value = 'Failed to load demand forecasts: ' + err.message
        console.error(err)
      } finally {
        loading.value = false
      }
    }

    const formatDeliveryDate = (dateStr) => {
      if (!dateStr) return 'N/A'
      const d = new Date(dateStr)
      if (isNaN(d.getTime())) return dateStr
      return d.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' })
    }

    const placeOrder = async () => {
      const itemsToOrder = enrichedForecasts.value.filter(i => i.allocatedQty > 0)
      submitting.value = true
      submitError.value = null
      try {
        const result = await api.createRestockingOrder({
          warehouse: selectedWarehouse.value,
          items: itemsToOrder.map(i => ({
            sku: i.item_sku,
            name: i.item_name,
            quantity: i.allocatedQty,
            unit_cost: i.unit_cost
          })),
          total_value: totalCost.value,
          budget: budget.value
        })
        submittedOrder.value = result
      } catch (err) {
        submitError.value = 'Failed to place order: ' + err.message
      } finally {
        submitting.value = false
      }
    }

    onMounted(loadForecasts)

    return {
      loading,
      error,
      budget,
      maxBudget,
      selectedWarehouse,
      enrichedForecasts,
      totalCost,
      remainingBudget,
      itemsToOrderCount,
      currencySymbol,
      submitting,
      submittedOrder,
      submitError,
      formatDeliveryDate,
      placeOrder
    }
  }
}
</script>

<style scoped>
.restocking {
  font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  padding: 2rem;
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

.card-subtitle {
  font-size: 0.813rem;
  color: #64748b;
  margin-top: 0.25rem;
  display: block;
}

/* Budget card */
.budget-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.budget-label {
  font-size: 0.875rem;
  font-weight: 600;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.budget-value {
  font-size: 2.25rem;
  font-weight: 700;
  color: #2563eb;
  letter-spacing: -0.025em;
}

.budget-slider {
  width: 100%;
  height: 6px;
  accent-color: #3b82f6;
  cursor: pointer;
  margin-bottom: 0.375rem;
}

.slider-bounds {
  display: flex;
  justify-content: space-between;
  font-size: 0.75rem;
  color: #94a3b8;
  margin-bottom: 1.25rem;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 1.25rem;
}

.stat-card {
  background: white;
  padding: 1.25rem;
  border-radius: 10px;
  border: 1px solid #e2e8f0;
}

.stat-label {
  font-size: 0.875rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: #64748b;
  margin-bottom: 0.625rem;
}

.stat-value {
  font-size: 2.25rem;
  font-weight: 700;
  color: #0f172a;
  letter-spacing: -0.025em;
}

/* Warehouse selector */
.warehouse-label {
  display: block;
  font-size: 0.875rem;
  color: #64748b;
  margin-bottom: 0.625rem;
}

.warehouse-select {
  padding: 0.5rem 0.75rem;
  border: 1px solid #cbd5e1;
  border-radius: 8px;
  font-size: 0.875rem;
  color: #0f172a;
  background: white;
  min-width: 200px;
  cursor: pointer;
  font-family: inherit;
}

.warehouse-select:focus {
  outline: none;
  border-color: #3b82f6;
}

/* Table */
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
  padding: 0.5rem 0.75rem;
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  font-weight: 600;
  color: #475569;
  text-align: left;
}

td {
  padding: 0.5rem 0.75rem;
  border-top: 1px solid #f1f5f9;
  color: #334155;
  font-size: 0.875rem;
}

.row-zeroed td {
  color: #94a3b8;
}

.dash {
  color: #94a3b8;
}

/* Table footer */
.tfoot-row td {
  border-top: 2px solid #e2e8f0;
  padding-top: 0.75rem;
  padding-bottom: 0.75rem;
}

.tfoot-label {
  font-weight: 600;
  color: #0f172a;
  font-size: 0.875rem;
}

.tfoot-total {
  font-weight: 700;
  color: #2563eb;
  font-size: 0.875rem;
}

/* Badges */
.badge {
  display: inline-block;
  padding: 0.313rem 0.75rem;
  border-radius: 6px;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.025em;
}

.badge.increasing {
  background: #d1fae5;
  color: #065f46;
}

.badge.decreasing {
  background: #fee2e2;
  color: #991b1b;
}

.badge.stable {
  background: #e0e7ff;
  color: #3730a3;
}

/* Action row */
.action-row {
  display: flex;
  justify-content: flex-end;
  margin-top: 0.5rem;
  margin-bottom: 1.5rem;
}

.place-order-btn {
  background: #2563eb;
  color: white;
  padding: 0.75rem 2rem;
  border-radius: 8px;
  font-size: 0.875rem;
  font-weight: 600;
  border: none;
  cursor: pointer;
  font-family: inherit;
  transition: background 0.15s;
}

.place-order-btn:hover:not(:disabled) {
  background: #1d4ed8;
}

.place-order-btn.btn-disabled,
.place-order-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Success banner */
.success-banner {
  background: #d1fae5;
  border: 1px solid #a7f3d0;
  border-radius: 10px;
  padding: 1.5rem;
  display: flex;
  align-items: flex-start;
  gap: 1rem;
  margin-bottom: 1.5rem;
}

.check-icon {
  width: 32px;
  height: 32px;
  flex-shrink: 0;
  margin-top: 0.125rem;
}

.success-title {
  font-size: 1rem;
  font-weight: 700;
  color: #065f46;
  margin-bottom: 0.375rem;
}

.success-detail {
  font-size: 0.875rem;
  color: #047857;
  margin-bottom: 0.25rem;
}

.orders-link {
  display: inline-block;
  margin-top: 0.5rem;
  font-size: 0.875rem;
  font-weight: 600;
  color: #2563eb;
  text-decoration: none;
}

.orders-link:hover {
  text-decoration: underline;
}
</style>
