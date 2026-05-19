<template>
  <Teleport to="body">
    <Transition name="modal">
      <div v-if="isOpen && backlogItem" class="modal-overlay" @click="close">
        <div class="modal-container" @click.stop>
          <div class="modal-header">
            <h3 class="modal-title">
              {{ mode === 'view' ? 'Purchase Order Details' : 'Create Purchase Order' }}
            </h3>
            <button class="close-button" @click="close">
              <svg width="20" height="20" viewBox="0 0 20 20" fill="none">
                <path d="M15 5L5 15M5 5L15 15" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
              </svg>
            </button>
          </div>

          <div class="modal-body">
            <!-- Item context header -->
            <div class="item-context">
              <div class="item-context-label">Item</div>
              <div class="item-context-name">{{ backlogItem.item_name }}</div>
              <div class="item-context-sku">SKU: {{ backlogItem.item_sku }}</div>
            </div>

            <!-- View mode: display existing PO data -->
            <template v-if="mode === 'view'">
              <div v-if="viewLoading" class="state-message">Loading purchase order...</div>
              <div v-else-if="viewError" class="state-message error">{{ viewError }}</div>
              <div v-else-if="poData" class="po-details">
                <div class="detail-grid">
                  <div class="detail-item">
                    <div class="detail-label">PO ID</div>
                    <div class="detail-value mono">{{ poData.id }}</div>
                  </div>
                  <div class="detail-item">
                    <div class="detail-label">Status</div>
                    <div class="detail-value">
                      <span class="status-badge" :class="poData.status">{{ poData.status }}</span>
                    </div>
                  </div>
                  <div class="detail-item">
                    <div class="detail-label">Supplier</div>
                    <div class="detail-value">{{ poData.supplier_name }}</div>
                  </div>
                  <div class="detail-item">
                    <div class="detail-label">Quantity</div>
                    <div class="detail-value">{{ poData.quantity }} units</div>
                  </div>
                  <div class="detail-item">
                    <div class="detail-label">Unit Cost</div>
                    <div class="detail-value">${{ Number(poData.unit_cost).toFixed(2) }}</div>
                  </div>
                  <div class="detail-item">
                    <div class="detail-label">Total Cost</div>
                    <div class="detail-value total">${{ (Number(poData.unit_cost) * Number(poData.quantity)).toFixed(2) }}</div>
                  </div>
                  <div class="detail-item">
                    <div class="detail-label">Expected Delivery</div>
                    <div class="detail-value">{{ formatDate(poData.expected_delivery_date) }}</div>
                  </div>
                  <div class="detail-item">
                    <div class="detail-label">Created</div>
                    <div class="detail-value">{{ formatDate(poData.created_date) }}</div>
                  </div>
                  <div v-if="poData.notes" class="detail-item full-width">
                    <div class="detail-label">Notes</div>
                    <div class="detail-value notes">{{ poData.notes }}</div>
                  </div>
                </div>
              </div>
            </template>

            <!-- Create mode: form -->
            <template v-else>
              <form class="po-form" @submit.prevent="submitForm">
                <div class="form-group">
                  <label class="form-label" for="supplier_name">Supplier Name <span class="required">*</span></label>
                  <input
                    id="supplier_name"
                    v-model="form.supplier_name"
                    type="text"
                    class="form-input"
                    :class="{ invalid: formErrors.supplier_name }"
                    placeholder="Enter supplier name"
                  />
                  <div v-if="formErrors.supplier_name" class="form-error">{{ formErrors.supplier_name }}</div>
                </div>

                <div class="form-row">
                  <div class="form-group">
                    <label class="form-label" for="quantity">Quantity <span class="required">*</span></label>
                    <input
                      id="quantity"
                      v-model.number="form.quantity"
                      type="number"
                      class="form-input"
                      :class="{ invalid: formErrors.quantity }"
                      min="1"
                    />
                    <div v-if="formErrors.quantity" class="form-error">{{ formErrors.quantity }}</div>
                  </div>

                  <div class="form-group">
                    <label class="form-label" for="unit_cost">Unit Cost ($) <span class="required">*</span></label>
                    <input
                      id="unit_cost"
                      v-model.number="form.unit_cost"
                      type="number"
                      class="form-input"
                      :class="{ invalid: formErrors.unit_cost }"
                      min="0"
                      step="0.01"
                      placeholder="0.00"
                    />
                    <div v-if="formErrors.unit_cost" class="form-error">{{ formErrors.unit_cost }}</div>
                  </div>
                </div>

                <div class="form-group">
                  <label class="form-label" for="expected_delivery_date">Expected Delivery Date <span class="required">*</span></label>
                  <input
                    id="expected_delivery_date"
                    v-model="form.expected_delivery_date"
                    type="date"
                    class="form-input"
                    :class="{ invalid: formErrors.expected_delivery_date }"
                    :min="minDeliveryDate"
                  />
                  <div v-if="formErrors.expected_delivery_date" class="form-error">{{ formErrors.expected_delivery_date }}</div>
                </div>

                <div class="form-group">
                  <label class="form-label" for="notes">Notes <span class="optional">(optional)</span></label>
                  <textarea
                    id="notes"
                    v-model="form.notes"
                    class="form-input form-textarea"
                    placeholder="Additional notes for this purchase order"
                    rows="3"
                  />
                </div>

                <div v-if="submitError" class="submit-error">{{ submitError }}</div>
              </form>
            </template>
          </div>

          <div class="modal-footer">
            <button class="btn-secondary" @click="close">
              {{ mode === 'view' ? 'Close' : 'Cancel' }}
            </button>
            <button
              v-if="mode === 'create'"
              class="btn-primary"
              :disabled="submitting"
              @click="submitForm"
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
import { ref, watch, computed } from 'vue'
import { api } from '../api'

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
    default: 'create',
    validator: (val) => ['create', 'view'].includes(val)
  }
})

const emit = defineEmits(['close', 'po-created'])

// View mode state
const viewLoading = ref(false)
const viewError = ref(null)
const poData = ref(null)

// Create mode state
const submitting = ref(false)
const submitError = ref(null)
const form = ref({
  supplier_name: '',
  quantity: 0,
  unit_cost: '',
  expected_delivery_date: '',
  notes: ''
})
const formErrors = ref({})

// Min delivery date = today
const minDeliveryDate = computed(() => {
  return new Date().toISOString().split('T')[0]
})

const resetForm = () => {
  form.value = {
    supplier_name: '',
    quantity: props.backlogItem ? props.backlogItem.quantity_needed : 0,
    unit_cost: '',
    expected_delivery_date: '',
    notes: ''
  }
  formErrors.value = {}
  submitError.value = null
}

const loadPO = async () => {
  if (!props.backlogItem) return
  viewLoading.value = true
  viewError.value = null
  poData.value = null
  try {
    poData.value = await api.getPurchaseOrderByBacklogItem(props.backlogItem.id)
  } catch (err) {
    viewError.value = 'Failed to load purchase order details.'
    console.error('PO load error:', err)
  } finally {
    viewLoading.value = false
  }
}

// When modal opens, initialise state based on mode
watch(
  () => props.isOpen,
  (isOpen) => {
    if (!isOpen) return
    if (props.mode === 'view') {
      loadPO()
    } else {
      resetForm()
    }
  }
)

// Also react if backlogItem changes while open
watch(
  () => props.backlogItem,
  () => {
    if (!props.isOpen) return
    if (props.mode === 'view') {
      loadPO()
    } else {
      resetForm()
    }
  }
)

const close = () => {
  emit('close')
}

const validateForm = () => {
  const errors = {}
  if (!form.value.supplier_name.trim()) {
    errors.supplier_name = 'Supplier name is required.'
  }
  if (!form.value.quantity || form.value.quantity < 1) {
    errors.quantity = 'Quantity must be at least 1.'
  }
  if (form.value.unit_cost === '' || form.value.unit_cost === null || Number(form.value.unit_cost) < 0) {
    errors.unit_cost = 'Unit cost must be 0 or greater.'
  }
  if (!form.value.expected_delivery_date) {
    errors.expected_delivery_date = 'Expected delivery date is required.'
  }
  formErrors.value = errors
  return Object.keys(errors).length === 0
}

const submitForm = async () => {
  if (!validateForm()) return
  submitting.value = true
  submitError.value = null
  try {
    const payload = {
      backlog_item_id: props.backlogItem.id,
      supplier_name: form.value.supplier_name.trim(),
      quantity: form.value.quantity,
      unit_cost: Number(form.value.unit_cost),
      expected_delivery_date: form.value.expected_delivery_date
    }
    // Only include notes if provided
    if (form.value.notes && form.value.notes.trim()) {
      payload.notes = form.value.notes.trim()
    }
    const created = await api.createPurchaseOrder(payload)
    emit('po-created', created)
  } catch (err) {
    submitError.value = 'Failed to create purchase order. Please try again.'
    console.error('PO create error:', err)
  } finally {
    submitting.value = false
  }
}

const formatDate = (dateString) => {
  if (!dateString) return 'N/A'
  const date = new Date(dateString)
  if (isNaN(date.getTime())) return 'N/A'
  return date.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'long',
    day: 'numeric'
  })
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
  background: #0f172a;
}

.modal-title {
  font-size: 1.125rem;
  font-weight: 700;
  color: #f8fafc;
  letter-spacing: -0.025em;
  margin: 0;
}

.close-button {
  background: none;
  border: none;
  color: #94a3b8;
  cursor: pointer;
  padding: 0.5rem;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 6px;
  transition: all 0.15s ease;
}

.close-button:hover {
  background: rgba(255, 255, 255, 0.1);
  color: #f8fafc;
}

.modal-body {
  flex: 1;
  overflow-y: auto;
  padding: 1.75rem;
}

/* Item context */
.item-context {
  padding: 1rem 1.25rem;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  margin-bottom: 1.75rem;
}

.item-context-label {
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: #64748b;
  margin-bottom: 0.25rem;
}

.item-context-name {
  font-size: 1rem;
  font-weight: 600;
  color: #0f172a;
  margin-bottom: 0.25rem;
}

.item-context-sku {
  font-size: 0.813rem;
  color: #64748b;
  font-family: 'Monaco', 'Courier New', monospace;
}

/* State messages */
.state-message {
  text-align: center;
  padding: 2rem;
  color: #64748b;
  font-size: 0.938rem;
}

.state-message.error {
  color: #dc2626;
}

/* PO detail view */
.detail-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 1.25rem;
}

.detail-item {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
}

.detail-item.full-width {
  grid-column: 1 / -1;
}

.detail-label {
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: #64748b;
}

.detail-value {
  font-size: 0.938rem;
  color: #0f172a;
  font-weight: 500;
}

.detail-value.mono {
  font-family: 'Monaco', 'Courier New', monospace;
  color: #2563eb;
  font-size: 0.813rem;
}

.detail-value.total {
  font-size: 1.125rem;
  font-weight: 700;
  color: #0f172a;
}

.detail-value.notes {
  color: #334155;
  font-weight: 400;
  line-height: 1.5;
}

.status-badge {
  display: inline-block;
  padding: 0.25rem 0.625rem;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.025em;
}

.status-badge.pending {
  background: #fef9c3;
  color: #854d0e;
}

.status-badge.approved {
  background: #dcfce7;
  color: #166534;
}

.status-badge.shipped {
  background: #dbeafe;
  color: #1e40af;
}

.status-badge.delivered {
  background: #d1fae5;
  color: #065f46;
}

.status-badge.cancelled {
  background: #fee2e2;
  color: #991b1b;
}

/* Form */
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
  gap: 0.375rem;
}

.form-label {
  font-size: 0.813rem;
  font-weight: 600;
  color: #334155;
}

.required {
  color: #dc2626;
}

.optional {
  color: #94a3b8;
  font-weight: 400;
}

.form-input {
  padding: 0.625rem 0.875rem;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  font-size: 0.875rem;
  color: #0f172a;
  font-family: inherit;
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
  background: white;
  width: 100%;
  box-sizing: border-box;
}

.form-input:focus {
  outline: none;
  border-color: #2563eb;
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
}

.form-input.invalid {
  border-color: #dc2626;
}

.form-input.invalid:focus {
  box-shadow: 0 0 0 3px rgba(220, 38, 38, 0.1);
}

.form-textarea {
  resize: vertical;
  min-height: 80px;
}

.form-error {
  font-size: 0.75rem;
  color: #dc2626;
  font-weight: 500;
}

.submit-error {
  padding: 0.75rem 1rem;
  background: #fef2f2;
  border: 1px solid #fecaca;
  border-radius: 8px;
  color: #dc2626;
  font-size: 0.875rem;
  font-weight: 500;
}

/* Footer */
.modal-footer {
  padding: 1.25rem 1.75rem;
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
  padding: 0.625rem 1.5rem;
  background: #2563eb;
  border: 1px solid #2563eb;
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
  border-color: #1d4ed8;
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
