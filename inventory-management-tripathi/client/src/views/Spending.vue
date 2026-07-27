<template>
  <div class="spending">
    <div class="page-header">
      <h2>{{ t('finance.title') }}</h2>
      <p>{{ t('finance.description') }}</p>
    </div>

    <div v-if="loading" class="loading">{{ t('common.loading') }}</div>
    <div v-else-if="error" class="error">{{ error }}</div>
    <div v-else>
      <!-- Revenue & Financial KPIs -->
      <div class="stats-grid-finance">
        <div class="stat-card revenue-card">
          <div class="stat-label">{{ t('finance.totalRevenue') }}</div>
          <div class="stat-value">{{ formatCurrency(revenueMetrics.totalRevenue) }}</div>
          <div class="stat-change positive">
            <span class="change-icon">↑</span>
            {{ t('finance.fromOrders', { count: revenueMetrics.orderCount }) }}
          </div>
        </div>
        <div class="stat-card cost-card">
          <div class="stat-label">{{ t('finance.totalCosts') }}</div>
          <div class="stat-value">{{ formatCurrency(totalCosts) }}</div>
          <div class="stat-meta">{{ t('finance.costBreakdown') }}</div>
        </div>
        <div class="stat-card profit-card">
          <div class="stat-label">{{ t('finance.netProfit') }}</div>
          <div class="stat-value">{{ formatCurrency(netProfit) }}</div>
          <div class="stat-meta">{{ profitMargin }}% {{ t('finance.margin') }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">{{ t('finance.avgOrderValue') }}</div>
          <div class="stat-value">{{ formatCurrency(revenueMetrics.avgOrderValue) }}</div>
          <div class="stat-meta">{{ t('finance.perOrderRevenue') }}</div>
        </div>
      </div>

      <!-- Monthly Revenue vs Cost Chart -->
      <div class="card chart-card">
        <div class="card-header">
          <h3 class="card-title">{{ t('finance.revenueVsCosts.title') }}</h3>
          <div class="chart-legend">
            <span class="legend-item"><span class="legend-dot revenue-color"></span>{{ t('finance.revenueVsCosts.revenue') }}</span>
            <span class="legend-item"><span class="legend-dot cost-color"></span>{{ t('finance.revenueVsCosts.costs') }}</span>
          </div>
        </div>
        <div class="chart-container">
          <div class="bar-chart">
            <div class="y-axis">
              <span>{{ currencySymbol }}{{ maxRevenueValue }}K</span>
              <span>{{ currencySymbol }}{{ Math.round(maxRevenueValue * 0.75) }}K</span>
              <span>{{ currencySymbol }}{{ Math.round(maxRevenueValue * 0.5) }}K</span>
              <span>{{ currencySymbol }}{{ Math.round(maxRevenueValue * 0.25) }}K</span>
              <span>{{ currencySymbol }}0</span>
            </div>
            <div class="chart-area">
              <div v-for="month in monthlyRevenue" :key="month.month" class="bar-group-revenue">
                <div class="revenue-bars">
                  <div class="revenue-bar" :style="{ height: getRevenueBarHeight(month.revenue) + '%' }" :title="`Revenue: ${currencySymbol}${month.revenue.toLocaleString()}`"></div>
                  <div class="cost-bar" :style="{ height: getRevenueBarHeight(month.costs) + '%' }" :title="`Costs: ${currencySymbol}${month.costs.toLocaleString()}`"></div>
                </div>
                <span class="bar-label">{{ translateMonth(month.month) }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Monthly Cost Flow Chart -->
      <div class="card chart-card">
        <div class="card-header">
          <h3 class="card-title">{{ t('finance.monthlyCostFlow.title') }}</h3>
          <div class="chart-legend">
            <span class="legend-item"><span class="legend-dot procurement"></span>{{ t('finance.monthlyCostFlow.procurement') }}</span>
            <span class="legend-item"><span class="legend-dot operational"></span>{{ t('finance.monthlyCostFlow.operational') }}</span>
            <span class="legend-item"><span class="legend-dot labor"></span>{{ t('finance.monthlyCostFlow.labor') }}</span>
            <span class="legend-item"><span class="legend-dot overhead"></span>{{ t('finance.monthlyCostFlow.overhead') }}</span>
          </div>
        </div>
        <div class="chart-container">
          <div class="bar-chart">
            <div class="y-axis">
              <span>{{ currencySymbol }}25K</span>
              <span>{{ currencySymbol }}20K</span>
              <span>{{ currencySymbol }}15K</span>
              <span>{{ currencySymbol }}10K</span>
              <span>{{ currencySymbol }}5K</span>
              <span>{{ currencySymbol }}0</span>
            </div>
            <div class="chart-area">
              <div v-for="month in monthlySpending" :key="month.month" class="bar-group">
                <div class="stacked-bar" @click="showCostDetail(month)">
                  <div class="bar-segment procurement" :style="{ height: getBarHeight(month.procurement) + '%' }" :title="`Procurement: ${currencySymbol}${month.procurement.toLocaleString()}`"></div>
                  <div class="bar-segment operational" :style="{ height: getBarHeight(month.operational) + '%' }" :title="`Operational: ${currencySymbol}${month.operational.toLocaleString()}`"></div>
                  <div class="bar-segment labor" :style="{ height: getBarHeight(month.labor) + '%' }" :title="`Labor: ${currencySymbol}${month.labor.toLocaleString()}`"></div>
                  <div class="bar-segment overhead" :style="{ height: getBarHeight(month.overhead) + '%' }" :title="`Overhead: ${currencySymbol}${month.overhead.toLocaleString()}`"></div>
                </div>
                <span class="bar-label">{{ translateMonth(month.month) }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div class="two-column-grid">
        <!-- Category Spending Breakdown -->
        <div class="card">
          <div class="card-header">
            <h3 class="card-title">{{ t('finance.categorySpending.title') }}</h3>
          </div>
          <div class="category-list">
            <div v-for="category in categorySpending" :key="category.category" class="category-item">
              <div class="category-info">
                <div class="category-name">{{ translateCategory(category.category) }}</div>
                <div class="category-amount">{{ currencySymbol }}{{ category.amount.toLocaleString() }}</div>
              </div>
              <div class="category-bar-container">
                <div class="category-bar" :style="{ width: category.percentage + '%' }"></div>
              </div>
              <div class="category-meta">
                <span class="percentage">{{ category.percentage }}% {{ t('finance.categorySpending.ofTotal') }}</span>
                <span class="change" :class="{ positive: category.change > 0, negative: category.change < 0 }">
                  {{ category.change > 0 ? '+' : '' }}{{ category.change }}%
                </span>
              </div>
            </div>
          </div>
        </div>

        <!-- Recent Transactions -->
        <div class="card transactions-card">
          <div class="card-header">
            <h3 class="card-title">{{ t('finance.transactions.title') }}</h3>
          </div>
          <div class="transactions-table-container">
            <table class="transactions-table">
              <thead>
                <tr>
                  <th>{{ t('finance.transactions.id') }}</th>
                  <th>{{ t('finance.transactions.description') }}</th>
                  <th>{{ t('finance.transactions.vendor') }}</th>
                  <th>{{ t('finance.transactions.date') }}</th>
                  <th class="text-right">{{ t('finance.transactions.amount') }}</th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="transaction in recentTransactions"
                  :key="transaction.id"
                  class="clickable-row"
                  @click="handleTransactionClick(transaction)"
                >
                  <td class="transaction-id">{{ transaction.id.toString().padStart(3, '0') }}</td>
                  <td class="transaction-description">{{ transaction.description }}</td>
                  <td class="transaction-vendor">{{ transaction.vendor }}</td>
                  <td class="transaction-date">{{ formatDateShort(transaction.date) }}</td>
                  <td class="transaction-amount text-right">{{ currencySymbol }}{{ transaction.amount.toLocaleString() }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>

    <CostDetailModal
      :is-open="showCostModal"
      :cost-data="selectedCostData"
      @close="showCostModal = false"
    />
  </div>
</template>

<script>
import { ref, onMounted, watch, computed } from 'vue'
import { api } from '../api'
import { useFilters } from '../composables/useFilters'
import { useI18n } from '../composables/useI18n'
import { formatCurrency as formatCurrencyUtil } from '../utils/currency'
import CostDetailModal from '../components/CostDetailModal.vue'

export default {
  name: 'Spending',
  components: {
    CostDetailModal
  },
  setup() {
    const { t, currentCurrency } = useI18n()
    const loading = ref(true)
    const error = ref(null)
    const allMonthlySpending = ref([])
    const allCategorySpending = ref([])
    const allTransactions = ref([])
    const summaryData = ref({})
    const allOrders = ref([])

    // Modal state
    const showCostModal = ref(false)
    const selectedCostData = ref(null)

    // Use shared filters
    const { selectedPeriod, getCurrentFilters } = useFilters()

    // Monthly spending chart always shows all months (not filtered)
    const monthlySpending = computed(() => {
      return allMonthlySpending.value
    })

    // Filtered monthly spending for summary calculations only
    const filteredMonthlySpending = computed(() => {
      if (selectedPeriod.value === 'all') {
        return allMonthlySpending.value
      }

      // Extract month name from YYYY-MM format
      const monthMap = {
        '01': 'Jan', '02': 'Feb', '03': 'Mar', '04': 'Apr',
        '05': 'May', '06': 'Jun', '07': 'Jul', '08': 'Aug',
        '09': 'Sep', '10': 'Oct', '11': 'Nov', '12': 'Dec'
      }
      const selectedMonth = monthMap[selectedPeriod.value.split('-')[1]]
      return allMonthlySpending.value.filter(m => m.month === selectedMonth)
    })

    const categorySpending = computed(() => {
      return allCategorySpending.value
    })

    const recentTransactions = computed(() => {
      if (selectedPeriod.value === 'all') {
        return allTransactions.value
      }
      // Filter transactions by selected month
      return allTransactions.value.filter(t => {
        const transactionMonth = new Date(t.date).toISOString().slice(0, 7)
        return transactionMonth === selectedPeriod.value
      })
    })

    const summary = computed(() => {
      // Recalculate summary based on filteredMonthlySpending (not the chart data)
      if (filteredMonthlySpending.value.length === 0) {
        return summaryData.value
      }

      const totals = filteredMonthlySpending.value.reduce((acc, month) => ({
        procurement: acc.procurement + month.procurement,
        operational: acc.operational + month.operational,
        labor: acc.labor + month.labor,
        overhead: acc.overhead + month.overhead
      }), { procurement: 0, operational: 0, labor: 0, overhead: 0 })

      return {
        total_procurement_cost: totals.procurement,
        total_operational_cost: totals.operational,
        total_labor_cost: totals.labor,
        total_overhead: totals.overhead,
        procurement_change: summaryData.value.procurement_change || 0,
        operational_change: summaryData.value.operational_change || 0,
        labor_change: summaryData.value.labor_change || 0,
        overhead_change: summaryData.value.overhead_change || 0
      }
    })

    // Filtered orders based on selected period
    const filteredOrders = computed(() => {
      if (selectedPeriod.value === 'all') {
        return allOrders.value
      }

      // Filter orders by selected month
      return allOrders.value.filter(order => {
        const orderMonth = new Date(order.order_date).toISOString().slice(0, 7)
        return orderMonth === selectedPeriod.value
      })
    })

    // Revenue metrics from filtered orders
    const revenueMetrics = computed(() => {
      const totalRevenue = filteredOrders.value.reduce((sum, order) => sum + (order.total_value || 0), 0)
      const orderCount = filteredOrders.value.length
      const avgOrderValue = orderCount > 0 ? totalRevenue / orderCount : 0

      return {
        totalRevenue,
        orderCount,
        avgOrderValue,
        revenueGrowth: 15.3 // Placeholder - could calculate from historical data
      }
    })

    // Total costs from summary
    const totalCosts = computed(() => {
      return summary.value.total_procurement_cost +
             summary.value.total_operational_cost +
             summary.value.total_labor_cost +
             summary.value.total_overhead
    })

    // Net profit
    const netProfit = computed(() => {
      return revenueMetrics.value.totalRevenue - totalCosts.value
    })

    // Profit margin percentage
    const profitMargin = computed(() => {
      if (revenueMetrics.value.totalRevenue === 0) return 0
      return ((netProfit.value / revenueMetrics.value.totalRevenue) * 100).toFixed(1)
    })

    // Monthly revenue data for chart
    const monthlyRevenue = computed(() => {
      const monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']

      // Initialize all months
      const revenueByMonth = monthNames.map(month => ({
        month,
        revenue: 0,
        costs: 0
      }))

      // Calculate revenue from orders
      allOrders.value.forEach(order => {
        const orderDate = new Date(order.order_date)
        const monthIndex = orderDate.getMonth()
        if (monthIndex >= 0 && monthIndex < 12) {
          revenueByMonth[monthIndex].revenue += order.total_value || 0
        }
      })

      // Add costs from spending data
      allMonthlySpending.value.forEach(spending => {
        const monthIndex = monthNames.indexOf(spending.month)
        if (monthIndex >= 0) {
          revenueByMonth[monthIndex].costs = spending.procurement + spending.operational + spending.labor + spending.overhead
        }
      })

      return revenueByMonth
    })

    // Max value for chart scaling
    const maxRevenueValue = computed(() => {
      const maxRevenue = Math.max(...monthlyRevenue.value.map(m => m.revenue))
      const maxCost = Math.max(...monthlyRevenue.value.map(m => m.costs))
      const max = Math.max(maxRevenue, maxCost)
      return Math.ceil(max / 1000) // Return in K
    })

    const loadData = async () => {
      try {
        loading.value = true
        const [summaryRes, monthlyRes, categoryRes, transactionsRes, ordersRes] = await Promise.all([
          api.getSpendingSummary(),
          api.getMonthlySpending(),
          api.getCategorySpending(),
          api.getTransactions(),
          api.getOrders()
        ])

        summaryData.value = summaryRes
        allMonthlySpending.value = monthlyRes
        allCategorySpending.value = categoryRes
        allTransactions.value = transactionsRes
        allOrders.value = ordersRes
      } catch (err) {
        error.value = 'Failed to load financial data: ' + err.message
      } finally {
        loading.value = false
      }
    }

    // Watch for period filter changes
    watch([selectedPeriod], () => {
      // Data will automatically update via computed properties
    })

    const formatCurrency = (value) => {
      return formatCurrencyUtil(value, currentCurrency.value)
    }

    const currencySymbol = computed(() => {
      return currentCurrency.value === 'JPY' ? '¥' : '$'
    })

    const getBarHeight = (value) => {
      const maxValue = 25000
      return (value / maxValue) * 100
    }

    const getRevenueBarHeight = (value) => {
      const maxValue = maxRevenueValue.value * 1000
      return (value / maxValue) * 100
    }

    const formatDate = (dateString) => {
      return new Date(dateString).toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric'
      })
    }

    const formatDateShort = (dateString) => {
      const date = new Date(dateString)
      const month = (date.getMonth() + 1).toString().padStart(2, '0')
      const day = date.getDate().toString().padStart(2, '0')
      const year = date.getFullYear().toString().slice(-2)
      return `${month}/${day}/${year}`
    }

    const translateMonth = (month) => {
      const monthMap = {
        'Jan': t('months.jan'),
        'Feb': t('months.feb'),
        'Mar': t('months.mar'),
        'Apr': t('months.apr'),
        'May': t('months.may'),
        'Jun': t('months.jun'),
        'Jul': t('months.jul'),
        'Aug': t('months.aug'),
        'Sep': t('months.sep'),
        'Oct': t('months.oct'),
        'Nov': t('months.nov'),
        'Dec': t('months.dec')
      }
      return monthMap[month] || month
    }

    const translateCategory = (category) => {
      // First try spending categories
      const spendingCategoryMap = {
        'Raw Materials': t('spendingCategories.rawMaterials'),
        'Components': t('spendingCategories.components'),
        'Equipment': t('spendingCategories.equipment'),
        'Consumables': t('spendingCategories.consumables')
      }

      // Then try product categories
      const productCategoryMap = {
        'Circuit Boards': t('categories.circuitBoards'),
        'Sensors': t('categories.sensors'),
        'Actuators': t('categories.actuators'),
        'Controllers': t('categories.controllers'),
        'Power Supplies': t('categories.powerSupplies')
      }

      return spendingCategoryMap[category] || productCategoryMap[category] || category
    }

    const handleTransactionClick = (transaction) => {
      console.log('Transaction clicked:', transaction)
      alert(`Transaction Details:\n\nID: ${transaction.id}\nDescription: ${transaction.description}\nVendor: ${transaction.vendor}\nDate: ${formatDateShort(transaction.date)}\nAmount: $${transaction.amount.toLocaleString()}`)
    }

    const showCostDetail = (monthData) => {
      selectedCostData.value = monthData
      showCostModal.value = true
    }

    onMounted(loadData)

    return {
      t,
      loading,
      error,
      summary,
      monthlySpending,
      categorySpending,
      recentTransactions,
      revenueMetrics,
      totalCosts,
      netProfit,
      profitMargin,
      monthlyRevenue,
      maxRevenueValue,
      formatCurrency,
      currencySymbol,
      getBarHeight,
      getRevenueBarHeight,
      formatDate,
      formatDateShort,
      translateMonth,
      translateCategory,
      handleTransactionClick,
      showCostModal,
      selectedCostData,
      showCostDetail,
      Math
    }
  }
}
</script>

<style scoped>
.stat-change {
  margin-top: 0.75rem;
  font-size: 0.875rem;
  display: flex;
  align-items: center;
  gap: 0.25rem;
}

.stat-change.positive {
  color: #059669;
}

.stat-change.negative {
  color: #dc2626;
}

.change-icon {
  font-weight: 700;
  font-size: 1rem;
}

.chart-card {
  margin-bottom: 1.75rem;
}

.chart-legend {
  display: flex;
  gap: 1.5rem;
  font-size: 0.875rem;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: #64748b;
}

.legend-dot {
  width: 12px;
  height: 12px;
  border-radius: 3px;
}

.legend-dot.procurement { background: #3b82f6; }
.legend-dot.operational { background: #8b5cf6; }
.legend-dot.labor { background: #10b981; }
.legend-dot.overhead { background: #f59e0b; }
.legend-dot.revenue-color { background: #0f172a; }
.legend-dot.cost-color { background: #ef4444; }

.stats-grid-finance {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
  gap: 1.5rem;
  margin-bottom: 2rem;
}

.revenue-card {
  border-left: 4px solid #0f172a;
}

.cost-card {
  border-left: 4px solid #ef4444;
}

.profit-card {
  border-left: 4px solid #3b82f6;
}

.stat-meta {
  margin-top: 0.5rem;
  font-size: 0.813rem;
  color: #64748b;
}

.bar-group-revenue {
  display: flex;
  flex-direction: column;
  align-items: center;
  flex: 1;
  height: 100%;
}

.revenue-bars {
  width: 100%;
  max-width: 80px;
  display: flex;
  gap: 6px;
  justify-content: center;
  align-items: flex-end;
  height: 100%;
  padding-bottom: 2rem;
}

.revenue-bar, .cost-bar {
  width: 50%;
  max-width: 30px;
  border-radius: 6px 6px 0 0;
  transition: all 0.3s ease;
  cursor: pointer;
  min-height: 4px;
}

.revenue-bar {
  background: #0f172a;
}

.cost-bar {
  background: #ef4444;
}

.revenue-bar:hover, .cost-bar:hover {
  opacity: 0.8;
  transform: scaleY(1.05);
}

.chart-container {
  padding: 1.5rem 0;
}

.bar-chart {
  display: flex;
  gap: 1.5rem;
  height: 350px;
}

.y-axis {
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  padding-right: 1rem;
  font-size: 0.75rem;
  color: #94a3b8;
  border-right: 1px solid #e2e8f0;
}

.chart-area {
  flex: 1;
  display: flex;
  align-items: flex-end;
  justify-content: space-around;
  gap: 0.5rem;
}

.bar-group {
  display: flex;
  flex-direction: column;
  align-items: center;
  flex: 1;
  height: 100%;
}

.stacked-bar {
  width: 100%;
  max-width: 60px;
  display: flex;
  flex-direction: column-reverse;
  align-items: stretch;
  height: 100%;
  padding-bottom: 2rem;
  cursor: pointer;
  transition: opacity 0.2s ease;
}

.stacked-bar:hover {
  opacity: 0.85;
}

.bar-segment {
  width: 100%;
  transition: all 0.3s ease;
  cursor: pointer;
  display: block;
}

.bar-segment:first-child {
  border-radius: 0 0 6px 6px;
}

.bar-segment:last-child {
  border-radius: 6px 6px 0 0;
}

.bar-segment.procurement { background: #3b82f6; }
.bar-segment.operational { background: #8b5cf6; }
.bar-segment.labor { background: #10b981; }
.bar-segment.overhead { background: #f59e0b; }

.bar-segment:hover {
  opacity: 0.8;
}

.bar-label {
  margin-top: 0.5rem;
  font-size: 0.75rem;
  font-weight: 600;
  color: #64748b;
}

.two-column-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(450px, 1fr));
  gap: 1.75rem;
}

.category-list {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.category-item {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.category-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.category-name {
  font-weight: 600;
  color: #0f172a;
}

.category-amount {
  font-weight: 700;
  color: #2563eb;
  font-size: 1.125rem;
}

.category-bar-container {
  width: 100%;
  height: 8px;
  background: #f1f5f9;
  border-radius: 4px;
  overflow: hidden;
}

.category-bar {
  height: 100%;
  background: linear-gradient(90deg, #3b82f6 0%, #2563eb 100%);
  border-radius: 4px;
  transition: width 0.6s ease;
}

.category-meta {
  display: flex;
  justify-content: space-between;
  font-size: 0.813rem;
}

.percentage {
  color: #64748b;
}

.change {
  font-weight: 600;
}

.change.positive {
  color: #059669;
}

.change.negative {
  color: #dc2626;
}

.transactions-card {
  display: flex;
  flex-direction: column;
}

.transactions-table-container {
  overflow-y: auto;
  max-height: 400px;
}

.transactions-table {
  width: 100%;
  border-collapse: collapse;
}

.transactions-table thead {
  position: sticky;
  top: 0;
  background: #f8fafc;
  z-index: 1;
}

.transactions-table th {
  text-align: left;
  padding: 0.625rem 0.75rem;
  font-weight: 600;
  color: #475569;
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  border-bottom: 1px solid #e2e8f0;
}

.transactions-table th.text-right {
  text-align: right;
}

.transactions-table td {
  padding: 0.75rem 0.75rem;
  border-bottom: 1px solid #f1f5f9;
  font-size: 0.875rem;
}

.transactions-table tbody tr {
  cursor: pointer;
  transition: background-color 0.15s ease;
}

.transactions-table tbody tr:hover {
  background: #f8fafc;
}

.transactions-table tbody tr.clickable-row:hover {
  background: #eff6ff;
}

.transaction-id {
  color: #64748b;
  font-weight: 500;
  font-family: 'Monaco', 'Courier New', monospace;
  font-size: 0.813rem;
}

.transaction-description {
  color: #0f172a;
  font-weight: 500;
}

.transaction-vendor {
  color: #64748b;
}

.transaction-date {
  color: #64748b;
  font-size: 0.813rem;
}

.transaction-amount {
  font-weight: 700;
  color: #0f172a;
}

.text-right {
  text-align: right;
}
</style>
