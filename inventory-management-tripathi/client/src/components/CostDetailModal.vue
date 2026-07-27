<template>
  <Teleport to="body">
    <Transition name="modal">
      <div v-if="isOpen && costData" class="modal-overlay" @click="close">
        <div class="modal-container" @click.stop>
          <div class="modal-header">
            <h3 class="modal-title">{{ costData.month }} Cost Breakdown</h3>
            <button class="close-button" @click="close">
              <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                <path d="M15 5L5 15M5 5L15 15" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
              </svg>
            </button>
          </div>

          <div class="modal-body">
            <div class="cost-summary">
              <div class="summary-card total">
                <div class="summary-label">Total Costs</div>
                <div class="summary-value">{{ currencySymbol }}{{ totalCosts.toLocaleString() }}</div>
              </div>
            </div>

            <div class="cost-breakdown">
              <div class="cost-item procurement">
                <div class="cost-header">
                  <div class="cost-icon">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
                      <rect x="4" y="6" width="16" height="14" rx="2" stroke="currentColor" stroke-width="2"/>
                      <path d="M8 6V4M16 6V4M4 10H20" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
                    </svg>
                  </div>
                  <div class="cost-info">
                    <div class="cost-name">Procurement</div>
                    <div class="cost-amount">{{ currencySymbol }}{{ costData.procurement.toLocaleString() }}</div>
                  </div>
                </div>
                <div class="cost-percentage">{{ getProcurementPercentage() }}% of total</div>
              </div>

              <div class="cost-item operational">
                <div class="cost-header">
                  <div class="cost-icon">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
                      <circle cx="12" cy="12" r="8" stroke="currentColor" stroke-width="2"/>
                      <path d="M12 8V12L15 15" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
                    </svg>
                  </div>
                  <div class="cost-info">
                    <div class="cost-name">Operational</div>
                    <div class="cost-amount">{{ currencySymbol }}{{ costData.operational.toLocaleString() }}</div>
                  </div>
                </div>
                <div class="cost-percentage">{{ getOperationalPercentage() }}% of total</div>
              </div>

              <div class="cost-item labor">
                <div class="cost-header">
                  <div class="cost-icon">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
                      <circle cx="12" cy="8" r="4" stroke="currentColor" stroke-width="2"/>
                      <path d="M6 20C6 16.6863 8.68629 14 12 14C15.3137 14 18 16.6863 18 20" stroke="currentColor" stroke-width="2"/>
                    </svg>
                  </div>
                  <div class="cost-info">
                    <div class="cost-name">Labor</div>
                    <div class="cost-amount">{{ currencySymbol }}{{ costData.labor.toLocaleString() }}</div>
                  </div>
                </div>
                <div class="cost-percentage">{{ getLaborPercentage() }}% of total</div>
              </div>

              <div class="cost-item overhead">
                <div class="cost-header">
                  <div class="cost-icon">
                    <svg width="24" height="24" viewBox="0 0 24 24" fill="none">
                      <path d="M3 12L5 10M5 10L12 3L19 10M5 10V20C5 20.5523 5.44772 21 6 21H9M19 10L21 12M19 10V20C19 20.5523 18.5523 21 18 21H15M9 21C9 21 9 18 9 16C9 14 10 14 12 14C14 14 15 14 15 16C15 18 15 21 15 21M9 21H15" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
                    </svg>
                  </div>
                  <div class="cost-info">
                    <div class="cost-name">Overhead</div>
                    <div class="cost-amount">{{ currencySymbol }}{{ costData.overhead.toLocaleString() }}</div>
                  </div>
                </div>
                <div class="cost-percentage">{{ getOverheadPercentage() }}% of total</div>
              </div>
            </div>
          </div>

          <div class="modal-footer">
            <button class="btn-secondary" @click="close">Close</button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { computed } from 'vue'
import { useI18n } from '../composables/useI18n'

const { currentCurrency } = useI18n()

const currencySymbol = computed(() => {
  return currentCurrency.value === 'JPY' ? '¥' : '$'
})

const props = defineProps({
  isOpen: {
    type: Boolean,
    default: false
  },
  costData: {
    type: Object,
    default: null
  }
})

const emit = defineEmits(['close'])

const totalCosts = computed(() => {
  if (!props.costData) return 0
  return props.costData.procurement + props.costData.operational +
         props.costData.labor + props.costData.overhead
})

const getProcurementPercentage = () => {
  if (!props.costData || totalCosts.value === 0) return 0
  return ((props.costData.procurement / totalCosts.value) * 100).toFixed(1)
}

const getOperationalPercentage = () => {
  if (!props.costData || totalCosts.value === 0) return 0
  return ((props.costData.operational / totalCosts.value) * 100).toFixed(1)
}

const getLaborPercentage = () => {
  if (!props.costData || totalCosts.value === 0) return 0
  return ((props.costData.labor / totalCosts.value) * 100).toFixed(1)
}

const getOverheadPercentage = () => {
  if (!props.costData || totalCosts.value === 0) return 0
  return ((props.costData.overhead / totalCosts.value) * 100).toFixed(1)
}

const close = () => {
  emit('close')
}
</script>

<style scoped>
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 2000;
  padding: 1rem;
}

.modal-container {
  background: white;
  border-radius: 12px;
  box-shadow: 0 20px 50px rgba(0, 0, 0, 0.15);
  max-width: 600px;
  width: 100%;
  max-height: 90vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 1.5rem;
  border-bottom: 1px solid #e2e8f0;
}

.modal-title {
  font-size: 1.25rem;
  font-weight: 700;
  color: #0f172a;
  letter-spacing: -0.025em;
}

.close-button {
  background: none;
  border: none;
  color: #64748b;
  cursor: pointer;
  padding: 0.5rem;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 6px;
  transition: all 0.15s ease;
}

.close-button:hover {
  background: #f1f5f9;
  color: #0f172a;
}

.modal-body {
  flex: 1;
  overflow-y: auto;
  padding: 2rem;
}

.cost-summary {
  margin-bottom: 2rem;
}

.summary-card {
  padding: 1.5rem;
  border-radius: 10px;
  text-align: center;
}

.summary-card.total {
  background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
  color: white;
}

.summary-label {
  font-size: 0.875rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  opacity: 0.9;
  margin-bottom: 0.5rem;
}

.summary-value {
  font-size: 2.25rem;
  font-weight: 700;
}

.cost-breakdown {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.cost-item {
  padding: 1.25rem;
  border-radius: 10px;
  border: 2px solid;
}

.cost-item.procurement {
  border-color: #93c5fd;
  background: #eff6ff;
}

.cost-item.operational {
  border-color: #c4b5fd;
  background: #f5f3ff;
}

.cost-item.labor {
  border-color: #86efac;
  background: #f0fdf4;
}

.cost-item.overhead {
  border-color: #fcd34d;
  background: #fffbeb;
}

.cost-header {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-bottom: 0.5rem;
}

.cost-icon {
  width: 48px;
  height: 48px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.cost-item.procurement .cost-icon {
  background: #3b82f6;
  color: white;
}

.cost-item.operational .cost-icon {
  background: #8b5cf6;
  color: white;
}

.cost-item.labor .cost-icon {
  background: #10b981;
  color: white;
}

.cost-item.overhead .cost-icon {
  background: #f59e0b;
  color: white;
}

.cost-info {
  flex: 1;
}

.cost-name {
  font-weight: 600;
  color: #0f172a;
  font-size: 1rem;
  margin-bottom: 0.25rem;
}

.cost-amount {
  font-size: 1.5rem;
  font-weight: 700;
  color: #0f172a;
}

.cost-percentage {
  font-size: 0.875rem;
  color: #64748b;
  font-weight: 500;
}

.modal-footer {
  padding: 1.5rem;
  border-top: 1px solid #e2e8f0;
  display: flex;
  justify-content: flex-end;
}

.btn-secondary {
  padding: 0.625rem 1.25rem;
  background: #f1f5f9;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  font-weight: 500;
  font-size: 0.875rem;
  color: #334155;
  cursor: pointer;
  transition: all 0.15s ease;
  font-family: inherit;
}

.btn-secondary:hover {
  background: #e2e8f0;
  border-color: #cbd5e1;
}

/* Modal transition animations */
.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.2s ease;
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}

.modal-enter-active .modal-container,
.modal-leave-active .modal-container {
  transition: transform 0.2s ease;
}

.modal-enter-from .modal-container,
.modal-leave-to .modal-container {
  transform: scale(0.95);
}
</style>
