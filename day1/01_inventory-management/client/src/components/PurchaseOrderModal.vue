<template>
  <Teleport to="body">
    <Transition name="modal">
      <div v-if="isOpen && backlogItem" class="modal-overlay" @click="close">
        <div class="modal-container" @click.stop>
          <div class="modal-header">
            <h3 class="modal-title">
              {{ mode === 'create' ? 'Create Purchase Order' : 'Purchase Order Details' }}
            </h3>
            <button class="close-button" @click="close">
              <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                <path d="M15 5L5 15M5 5L15 15" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
              </svg>
            </button>
          </div>

          <div class="modal-body">
            <!-- Item header shown in both modes -->
            <div class="item-header">
              <div class="item-title-section">
                <h4 class="item-name">{{ translateProductName(backlogItem.item_name) }}</h4>
                <div class="item-sku">SKU: {{ backlogItem.item_sku }}</div>
              </div>
              <span class="priority-badge" :class="backlogItem.priority">
                {{ backlogItem.priority }} Priority
              </span>
            </div>

            <!-- CREATE MODE: form -->
            <template v-if="mode === 'create'">
              <div v-if="submitError" class="error-banner">{{ submitError }}</div>

              <form class="po-form" @submit.prevent="submitPO">
                <div class="form-group">
                  <label class="form-label" for="supplier-name">Supplier Name <span class="required">*</span></label>
                  <input
                    id="supplier-name"
                    v-model="form.supplier_name"
                    type="text"
                    class="form-input"
                    placeholder="Enter supplier name"
                    required
                  />
                </div>

                <div class="form-row">
                  <div class="form-group">
                    <label class="form-label" for="quantity">Quantity <span class="required">*</span></label>
                    <input
                      id="quantity"
                      v-model.number="form.quantity"
                      type="number"
                      class="form-input"
                      min="1"
                      required
                    />
                  </div>

                  <div class="form-group">
                    <label class="form-label" for="unit-cost">Unit Cost ($) <span class="required">*</span></label>
                    <input
                      id="unit-cost"
                      v-model.number="form.unit_cost"
                      type="number"
                      class="form-input"
                      min="0"
                      step="0.01"
                      placeholder="0.00"
                      required
                    />
                  </div>
                </div>

                <div class="form-group">
                  <label class="form-label" for="delivery-date">Expected Delivery Date <span class="required">*</span></label>
                  <input
                    id="delivery-date"
                    v-model="form.expected_delivery_date"
                    type="date"
                    class="form-input"
                    required
                  />
                </div>

                <div class="form-group">
                  <label class="form-label" for="notes">Notes</label>
                  <textarea
                    id="notes"
                    v-model="form.notes"
                    class="form-textarea"
                    rows="3"
                    placeholder="Optional notes for this purchase order"
                  ></textarea>
                </div>

                <div class="total-estimate" v-if="form.quantity && form.unit_cost">
                  <span class="total-label">Estimated Total</span>
                  <span class="total-value">{{ formatCurrency(form.quantity * form.unit_cost) }}</span>
                </div>
              </form>
            </template>

            <!-- VIEW MODE: read-only PO details -->
            <template v-else-if="mode === 'view'">
              <div v-if="viewLoading" class="state-message">Loading purchase order...</div>
              <div v-else-if="viewError" class="error-banner">{{ viewError }}</div>
              <div v-else-if="purchaseOrder" class="info-grid">
                <div class="info-item">
                  <div class="info-label">PO ID</div>
                  <div class="info-value sku">{{ purchaseOrder.id }}</div>
                </div>

                <div class="info-item">
                  <div class="info-label">Supplier</div>
                  <div class="info-value">{{ purchaseOrder.supplier_name }}</div>
                </div>

                <div class="info-item">
                  <div class="info-label">Quantity</div>
                  <div class="info-value">{{ purchaseOrder.quantity }} units</div>
                </div>

                <div class="info-item">
                  <div class="info-label">Unit Cost</div>
                  <div class="info-value">{{ formatCurrency(purchaseOrder.unit_cost) }}</div>
                </div>

                <div class="info-item">
                  <div class="info-label">Total Value</div>
                  <div class="info-value">{{ formatCurrency(purchaseOrder.quantity * purchaseOrder.unit_cost) }}</div>
                </div>

                <div class="info-item">
                  <div class="info-label">Status</div>
                  <div class="info-value">
                    <span class="badge" :class="statusClass(purchaseOrder.status)">
                      {{ purchaseOrder.status }}
                    </span>
                  </div>
                </div>

                <div class="info-item">
                  <div class="info-label">Expected Delivery</div>
                  <div class="info-value">{{ formatDate(purchaseOrder.expected_delivery_date) }}</div>
                </div>

                <div class="info-item">
                  <div class="info-label">Created Date</div>
                  <div class="info-value">{{ formatDate(purchaseOrder.created_date) }}</div>
                </div>

                <div v-if="purchaseOrder.notes" class="info-item info-item-full">
                  <div class="info-label">Notes</div>
                  <div class="info-value">{{ purchaseOrder.notes }}</div>
                </div>
              </div>
            </template>
          </div>

          <div class="modal-footer">
            <button class="btn-secondary" @click="close">
              {{ mode === 'create' ? 'Cancel' : 'Close' }}
            </button>
            <button
              v-if="mode === 'create'"
              class="btn-primary"
              :disabled="submitting"
              @click="submitPO"
            >
              {{ submitting ? 'Creating...' : 'Create Purchase Order' }}
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useI18n } from '../composables/useI18n'
import { api } from '../api'

const { translateProductName } = useI18n()

const props = defineProps({
  isOpen: {
    type: Boolean,
    default: false
  },
  backlogItem: {
    type: Object,
    default: null
  },
  mode: {
    type: String,
    default: 'create', // 'create' | 'view'
    validator: (v) => ['create', 'view'].includes(v)
  }
})

const emit = defineEmits(['close', 'po-created'])

// --- Shared state ---

const close = () => emit('close')

const formatDate = (dateString) => {
  if (!dateString) return 'N/A'
  const date = new Date(dateString)
  // Validate before formatting to avoid NaN display
  if (isNaN(date.getTime())) return dateString
  return date.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'long',
    day: 'numeric'
  })
}

const formatCurrency = (value) => {
  if (value == null) return '$0.00'
  return value.toLocaleString('en-US', { style: 'currency', currency: 'USD' })
}

const statusClass = (status) => {
  if (!status) return ''
  switch (status.toLowerCase()) {
    case 'pending': return 'warning'
    case 'confirmed':
    case 'delivered': return 'success'
    case 'cancelled': return 'danger'
    default: return 'info'
  }
}

// --- CREATE mode ---

// Default quantity to the shortage amount when backlogItem is available
const defaultQuantity = computed(() => {
  if (!props.backlogItem) return 1
  const shortage = props.backlogItem.quantity_needed - props.backlogItem.quantity_available
  return shortage > 0 ? shortage : 1
})

const form = ref({
  supplier_name: '',
  quantity: 1,
  unit_cost: null,
  expected_delivery_date: '',
  notes: ''
})

const submitting = ref(false)
const submitError = ref(null)

// Reset form and pre-fill quantity whenever the modal opens in create mode
watch(
  () => [props.isOpen, props.mode, props.backlogItem],
  ([open, mode]) => {
    if (open && mode === 'create') {
      form.value = {
        supplier_name: '',
        quantity: defaultQuantity.value,
        unit_cost: null,
        expected_delivery_date: '',
        notes: ''
      }
      submitError.value = null
      submitting.value = false
    }
  },
  { immediate: false }
)

const submitPO = async () => {
  if (submitting.value) return
  submitting.value = true
  submitError.value = null

  try {
    const payload = {
      backlog_item_id: props.backlogItem.id,
      supplier_name: form.value.supplier_name,
      quantity: form.value.quantity,
      unit_cost: form.value.unit_cost,
      expected_delivery_date: form.value.expected_delivery_date,
      notes: form.value.notes || null
    }
    const response = await api.createPurchaseOrder(payload)
    emit('po-created', response.data)
  } catch (err) {
    // Surface a meaningful error message if the API provides one
    submitError.value =
      err?.response?.data?.detail || 'Failed to create purchase order. Please try again.'
    console.error('PO creation error:', err)
  } finally {
    submitting.value = false
  }
}

// --- VIEW mode ---

const purchaseOrder = ref(null)
const viewLoading = ref(false)
const viewError = ref(null)

const fetchPO = async () => {
  if (!props.backlogItem) return
  viewLoading.value = true
  viewError.value = null
  purchaseOrder.value = null

  try {
    const response = await api.getPurchaseOrderByBacklogItem(props.backlogItem.id)
    purchaseOrder.value = response.data
  } catch (err) {
    viewError.value =
      err?.response?.data?.detail || 'Failed to load purchase order details.'
    console.error('PO fetch error:', err)
  } finally {
    viewLoading.value = false
  }
}

// Fetch PO details whenever the modal opens in view mode
watch(
  () => [props.isOpen, props.mode, props.backlogItem?.id],
  ([open, mode]) => {
    if (open && mode === 'view') {
      fetchPO()
    }
  },
  { immediate: false }
)
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

/* Item header */
.item-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  padding-bottom: 1.5rem;
  border-bottom: 1px solid #e2e8f0;
  margin-bottom: 1.5rem;
}

.item-title-section {
  min-width: 0;
}

.item-name {
  font-size: 1.125rem;
  font-weight: 700;
  color: #0f172a;
  margin: 0 0 0.375rem 0;
}

.item-sku {
  font-size: 0.875rem;
  color: #64748b;
  font-family: 'Monaco', 'Courier New', monospace;
}

.priority-badge {
  padding: 0.375rem 0.75rem;
  border-radius: 6px;
  font-size: 0.813rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.025em;
  flex-shrink: 0;
}

.priority-badge.high {
  background: #fecaca;
  color: #991b1b;
}

.priority-badge.medium {
  background: #fed7aa;
  color: #92400e;
}

.priority-badge.low {
  background: #dbeafe;
  color: #1e40af;
}

/* Error banner */
.error-banner {
  background: #fef2f2;
  border: 1px solid #fecaca;
  border-radius: 8px;
  color: #dc2626;
  font-size: 0.875rem;
  padding: 0.75rem 1rem;
  margin-bottom: 1.25rem;
}

/* Form styles */
.po-form {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 1rem;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.form-label {
  font-size: 0.813rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: #64748b;
}

.required {
  color: #dc2626;
}

.form-input,
.form-textarea {
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 0.625rem 0.875rem;
  font-size: 0.9375rem;
  color: #0f172a;
  background: #f8fafc;
  font-family: inherit;
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
  width: 100%;
  box-sizing: border-box;
}

.form-input:focus,
.form-textarea:focus {
  outline: none;
  border-color: #2563eb;
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
  background: white;
}

.form-textarea {
  resize: vertical;
  min-height: 80px;
}

.total-estimate {
  display: flex;
  align-items: center;
  justify-content: space-between;
  background: #f0f9ff;
  border: 1px solid #bae6fd;
  border-radius: 8px;
  padding: 0.875rem 1rem;
}

.total-label {
  font-size: 0.875rem;
  font-weight: 600;
  color: #0369a1;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.total-value {
  font-size: 1.25rem;
  font-weight: 700;
  color: #0f172a;
}

/* View mode info grid */
.info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1.5rem;
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

/* Span full width for notes field */
.info-item-full {
  grid-column: 1 / -1;
}

.info-label {
  font-size: 0.813rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: #64748b;
}

.info-value {
  font-size: 0.9375rem;
  color: #0f172a;
  font-weight: 500;
}

.info-value.sku {
  font-family: 'Monaco', 'Courier New', monospace;
  color: #2563eb;
}

/* Status badges */
.badge {
  display: inline-block;
  padding: 0.25rem 0.625rem;
  border-radius: 4px;
  font-size: 0.813rem;
  font-weight: 600;
  text-transform: capitalize;
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

/* Loading / empty state */
.state-message {
  color: #64748b;
  font-size: 0.9375rem;
  text-align: center;
  padding: 2rem 0;
}

/* Footer */
.modal-footer {
  padding: 1.5rem;
  border-top: 1px solid #e2e8f0;
  display: flex;
  justify-content: flex-end;
  gap: 0.75rem;
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

.btn-primary {
  padding: 0.625rem 1.25rem;
  background: #2563eb;
  border: 1px solid transparent;
  border-radius: 8px;
  font-weight: 600;
  font-size: 0.875rem;
  color: white;
  cursor: pointer;
  transition: all 0.15s ease;
  font-family: inherit;
}

.btn-primary:hover:not(:disabled) {
  background: #1d4ed8;
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
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
