<template>
  <div class="reports">
    <div class="page-header">
      <h2>Performance Reports</h2>
      <p>View quarterly performance metrics and monthly trends</p>
    </div>

    <div v-if="loading" class="loading">Loading reports...</div>
    <div v-else-if="error" class="error">{{ error }}</div>
    <div v-else>
      <!-- Quarterly Performance -->
      <div class="card">
        <div class="card-header">
          <h3 class="card-title">Quarterly Performance</h3>
        </div>
        <div class="table-container">
          <table class="reports-table">
            <thead>
              <tr>
                <th>Quarter</th>
                <th>Total Orders</th>
                <th>Total Revenue</th>
                <th>Avg Order Value</th>
                <th>Fulfillment Rate</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(q, index) in quarterlyData" :key="index">
                <td><strong>{{ q.quarter }}</strong></td>
                <td>{{ q.total_orders }}</td>
                <td>${{ formatNumber(q.total_revenue) }}</td>
                <td>${{ formatNumber(q.avg_order_value) }}</td>
                <td>
                  <span :class="getFulfillmentClass(q.fulfillment_rate)">
                    {{ q.fulfillment_rate }}%
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Monthly Trends Chart -->
      <div class="card">
        <div class="card-header">
          <h3 class="card-title">Monthly Revenue Trend</h3>
        </div>
        <div class="chart-container">
          <div class="bar-chart">
            <div v-for="(month, index) in monthlyData" :key="index" class="bar-wrapper">
              <div class="bar-container">
                <div
                  class="bar"
                  :style="{ height: getBarHeight(month.revenue) + 'px' }"
                  :title="'$' + formatNumber(month.revenue)"
                ></div>
              </div>
              <div class="bar-label">{{ formatMonth(month.month) }}</div>
            </div>
          </div>
        </div>
      </div>

      <!-- Month-over-Month Comparison -->
      <div class="card">
        <div class="card-header">
          <h3 class="card-title">Month-over-Month Analysis</h3>
        </div>
        <div class="table-container">
          <table class="reports-table">
            <thead>
              <tr>
                <th>Month</th>
                <th>Orders</th>
                <th>Revenue</th>
                <th>Change</th>
                <th>Growth Rate</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(month, index) in monthlyData" :key="index">
                <td><strong>{{ formatMonth(month.month) }}</strong></td>
                <td>{{ month.order_count }}</td>
                <td>${{ formatNumber(month.revenue) }}</td>
                <td>
                  <span v-if="index > 0" :class="getChangeClass(month.revenue, monthlyData[index - 1].revenue)">
                    {{ getChangeValue(month.revenue, monthlyData[index - 1].revenue) }}
                  </span>
                  <span v-else>-</span>
                </td>
                <td>
                  <span v-if="index > 0" :class="getChangeClass(month.revenue, monthlyData[index - 1].revenue)">
                    {{ getGrowthRate(month.revenue, monthlyData[index - 1].revenue) }}
                  </span>
                  <span v-else>-</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Summary Stats -->
      <div class="stats-grid">
        <div class="stat-card">
          <div class="stat-label">Total Revenue (YTD)</div>
          <div class="stat-value">${{ formatNumber(totalRevenue) }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">Avg Monthly Revenue</div>
          <div class="stat-value">${{ formatNumber(avgMonthlyRevenue) }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">Total Orders (YTD)</div>
          <div class="stat-value">{{ totalOrders }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">Best Performing Quarter</div>
          <div class="stat-value">{{ bestQuarter }}</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import axios from 'axios'

export default {
  name: 'Reports',
  data() {
    return {
      loading: true,
      error: null,
      quarterlyData: [],
      monthlyData: [],
      totalRevenue: 0,
      avgMonthlyRevenue: 0,
      totalOrders: 0,
      bestQuarter: ''
    }
  },
  mounted() {
    console.log('Reports component mounted')
    this.loadData()
  },
  methods: {
    async loadData() {
      console.log('Loading reports data...')
      try {
        this.loading = true

        // Fetch quarterly data
        console.log('Fetching quarterly data...')
        const quarterlyResponse = await axios.get('http://localhost:8001/api/reports/quarterly')
        this.quarterlyData = quarterlyResponse.data
        console.log('Quarterly data:', this.quarterlyData)

        // Fetch monthly data
        console.log('Fetching monthly data...')
        const monthlyResponse = await axios.get('http://localhost:8001/api/reports/monthly-trends')
        this.monthlyData = monthlyResponse.data
        console.log('Monthly data:', this.monthlyData)

        // Calculate summary stats
        console.log('Calculating summary stats...')
        this.calculateSummaryStats()
        console.log('Summary stats calculated')

      } catch (err) {
        console.log('Error loading reports:', err)
        this.error = 'Failed to load reports: ' + err.message
      } finally {
        this.loading = false
        console.log('Loading complete')
      }
    },

    calculateSummaryStats() {
      // Calculate total revenue
      var total = 0
      for (var i = 0; i < this.monthlyData.length; i++) {
        total = total + this.monthlyData[i].revenue
      }
      this.totalRevenue = total

      // Calculate average monthly revenue
      if (this.monthlyData.length > 0) {
        this.avgMonthlyRevenue = total / this.monthlyData.length
      } else {
        this.avgMonthlyRevenue = 0
      }

      // Calculate total orders
      var orders = 0
      for (var i = 0; i < this.monthlyData.length; i++) {
        orders = orders + this.monthlyData[i].order_count
      }
      this.totalOrders = orders

      // Find best quarter
      var bestQ = ''
      var bestRevenue = 0
      for (var i = 0; i < this.quarterlyData.length; i++) {
        if (this.quarterlyData[i].total_revenue > bestRevenue) {
          bestRevenue = this.quarterlyData[i].total_revenue
          bestQ = this.quarterlyData[i].quarter
        }
      }
      this.bestQuarter = bestQ
    },

    formatNumber(num) {
      console.log('Formatting number:', num)
      // Format number with commas
      var str = num.toString()
      var parts = str.split('.')
      var intPart = parts[0]
      var decPart = parts.length > 1 ? parts[1] : '00'

      var formatted = ''
      var count = 0
      for (var i = intPart.length - 1; i >= 0; i--) {
        if (count > 0 && count % 3 === 0) {
          formatted = ',' + formatted
        }
        formatted = intPart[i] + formatted
        count++
      }

      if (decPart.length === 1) {
        decPart = decPart + '0'
      }
      if (decPart.length > 2) {
        decPart = decPart.substring(0, 2)
      }

      return formatted + '.' + decPart
    },

    formatMonth(monthStr) {
      console.log('Formatting month:', monthStr)
      // Convert YYYY-MM to readable format
      var parts = monthStr.split('-')
      var year = parts[0]
      var month = parts[1]

      var monthNames = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
      var monthIndex = parseInt(month) - 1

      return monthNames[monthIndex] + ' ' + year
    },

    getBarHeight(revenue) {
      console.log('Calculating bar height for revenue:', revenue)
      // Calculate bar height (max height 200px)
      var maxRevenue = 0
      for (var i = 0; i < this.monthlyData.length; i++) {
        if (this.monthlyData[i].revenue > maxRevenue) {
          maxRevenue = this.monthlyData[i].revenue
        }
      }

      if (maxRevenue === 0) {
        return 0
      }

      var height = (revenue / maxRevenue) * 200
      return height
    },

    getFulfillmentClass(rate) {
      if (rate >= 90) {
        return 'badge success'
      } else if (rate >= 75) {
        return 'badge warning'
      } else {
        return 'badge danger'
      }
    },

    getChangeValue(current, previous) {
      var change = current - previous
      if (change > 0) {
        return '+$' + this.formatNumber(change)
      } else if (change < 0) {
        return '-$' + this.formatNumber(Math.abs(change))
      } else {
        return '$0.00'
      }
    },

    getChangeClass(current, previous) {
      var change = current - previous
      if (change > 0) {
        return 'positive-change'
      } else if (change < 0) {
        return 'negative-change'
      } else {
        return ''
      }
    },

    getGrowthRate(current, previous) {
      if (previous === 0) {
        return 'N/A'
      }

      var rate = ((current - previous) / previous) * 100
      var sign = rate > 0 ? '+' : ''

      return sign + rate.toFixed(1) + '%'
    }
  }
}
</script>

<style scoped>
.reports {
  padding: 0;
}

.card {
  background: white;
  border-radius: 12px;
  padding: 1.5rem;
  margin-bottom: 1.5rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.card-header {
  margin-bottom: 1.5rem;
}

.card-title {
  font-size: 1.25rem;
  font-weight: 600;
  color: #0f172a;
  margin: 0;
}

.reports-table {
  width: 100%;
  border-collapse: collapse;
}

.reports-table th {
  background: #f8fafc;
  padding: 0.75rem;
  text-align: left;
  font-weight: 600;
  color: #64748b;
  border-bottom: 2px solid #e2e8f0;
}

.reports-table td {
  padding: 0.75rem;
  border-bottom: 1px solid #e2e8f0;
}

.reports-table tr:hover {
  background: #f8fafc;
}

.chart-container {
  padding: 2rem 1rem;
  min-height: 300px;
}

.bar-chart {
  display: flex;
  align-items: flex-end;
  justify-content: space-around;
  height: 250px;
  gap: 0.5rem;
}

.bar-wrapper {
  display: flex;
  flex-direction: column;
  align-items: center;
  flex: 1;
  max-width: 80px;
}

.bar-container {
  height: 200px;
  display: flex;
  align-items: flex-end;
  width: 100%;
}

.bar {
  width: 100%;
  background: linear-gradient(to top, #3b82f6, #60a5fa);
  border-radius: 4px 4px 0 0;
  transition: all 0.3s;
  cursor: pointer;
}

.bar:hover {
  background: linear-gradient(to top, #2563eb, #3b82f6);
}

.bar-label {
  margin-top: 0.5rem;
  font-size: 0.75rem;
  color: #64748b;
  text-align: center;
  transform: rotate(-45deg);
  white-space: nowrap;
  margin-top: 1.5rem;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 1rem;
  margin-top: 1.5rem;
}

.stat-card {
  background: white;
  border-radius: 12px;
  padding: 1.5rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
  border-left: 4px solid #3b82f6;
}

.stat-label {
  font-size: 0.875rem;
  color: #64748b;
  margin-bottom: 0.5rem;
}

.stat-value {
  font-size: 1.875rem;
  font-weight: 700;
  color: #0f172a;
}

.badge {
  padding: 0.25rem 0.75rem;
  border-radius: 9999px;
  font-size: 0.875rem;
  font-weight: 500;
}

.badge.success {
  background: #dcfce7;
  color: #166534;
}

.badge.warning {
  background: #fef3c7;
  color: #92400e;
}

.badge.danger {
  background: #fee2e2;
  color: #991b1b;
}

.positive-change {
  color: #16a34a;
  font-weight: 600;
}

.negative-change {
  color: #dc2626;
  font-weight: 600;
}

.loading {
  text-align: center;
  padding: 3rem;
  color: #64748b;
}

.error {
  background: #fee2e2;
  color: #991b1b;
  padding: 1rem;
  border-radius: 8px;
  margin: 1rem 0;
}
</style>
