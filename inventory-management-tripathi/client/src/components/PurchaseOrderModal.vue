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
            <div v-if="mode === 'create'">
              <div class="item-context">
                <div class="context-label">Item</div>
                <div class="context-value">{{ backlogItem.item_name }} <span class="sku">{{ backlogItem.item_sku }}</span></div>
              </div>

              <form @submit.prevent="submitPO" class="po-form">
                <div class="field">
                  <label class="field-label" for="supplier">Supplier</label>
                  <input
                    id="supplier"
                    v-model="form.supplier"
                    type="text"
                    class="field-input"
                    placeholder="Supplier name"
                    required
                  />
                </div>

                <div class="field">
                  <label class="field-label" for="quantity">Quantity to Order</label>
                  <input
                    id="quantity"
                    v-model.number="form.quantity"
                    type="number"
                    class="field-input"
                    placeholder="Units"
                    min="1"
                    required
                  />
                </div>

                <div class="field">
                  <label class="field-label" for="expected_date">Expected Delivery Date</label>
                  <input
                    id="expected_date"
                    v-model="form.expected_date"
                    type="date"
                    class="field-input"
                    required
                  />
                </div>

                <div class="modal-footer">
                  <button type="button" class="btn-secondary" @click="close">Cancel</button>
                  <button type="submit" class="btn-primary">Submit Order</button>
                </div>
              </form>
            </div>

            <div v-else class="po-view">
              <div v-if="backlogItem.purchase_order" class="info-grid">
                <div class="info-item">
                  <div class="info-label">Supplier</div>
                  <div class="info-value">{{ backlogItem.purchase_order.supplier_name }}</div>
                </div>
                <div class="info-item">
                  <div class="info-label">Quantity</div>
                  <div class="info-value">{{ backlogItem.purchase_order.quantity }} units</div>
                </div>
                <div class="info-item">
                  <div class="info-label">Expected Delivery</div>
                  <div class="info-value">{{ formatDate(backlogItem.purchase_order.expected_delivery_date) }}</div>
                </div>
                <div class="info-item">
                  <div class="info-label">Status</div>
                  <div class="info-value">
                    <span class="badge">{{ backlogItem.purchase_order.status }}</span>
                  </div>
                </div>
              </div>
              <div v-else class="no-po">No purchase order on record.</div>

              <div class="modal-footer">
                <button class="btn-secondary" @click="close">Close</button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { reactive } from 'vue'

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
    default: 'create'
  }
})

const emit = defineEmits(['close', 'po-created'])

const form = reactive({
  supplier: '',
  quantity: null,
  expected_date: ''
})

const close = () => {
  emit('close')
}

const submitPO = () => {
  const po = {
    id: `PO-${Date.now().toString(36).toUpperCase()}`,
    backlog_item_id: props.backlogItem.id,
    supplier: form.supplier,
    quantity: form.quantity,
    expected_date: form.expected_date,
    status: 'pending'
  }
  emit('po-created', po)
  form.supplier = ''
  form.quantity = null
  form.expected_date = ''
}

const formatDate = (dateString) => {
  if (!dateString) return 'N/A'
  const date = new Date(dateString)
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
  max-width: 520px;
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
  padding: 1.5rem;
}

.item-context {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 1rem;
  margin-bottom: 1.5rem;
}

.context-label {
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: #64748b;
  margin-bottom: 0.25rem;
}

.context-value {
  font-size: 0.938rem;
  font-weight: 600;
  color: #0f172a;
}

.sku {
  font-family: 'Monaco', 'Courier New', monospace;
  color: #2563eb;
  font-weight: 400;
  margin-left: 0.5rem;
}

.po-form {
  display: flex;
  flex-direction: column;
  gap: 1.25rem;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
}

.field-label {
  font-size: 0.813rem;
  font-weight: 600;
  color: #374151;
}

.field-input {
  padding: 0.625rem 0.875rem;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  font-size: 0.875rem;
  color: #0f172a;
  font-family: inherit;
  transition: border-color 0.15s ease;
  outline: none;
}

.field-input:focus {
  border-color: #2563eb;
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 1.25rem;
  margin-bottom: 1rem;
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 0.375rem;
}

.info-label {
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: #64748b;
}

.info-value {
  font-size: 0.938rem;
  color: #0f172a;
  font-weight: 500;
}

.badge {
  display: inline-block;
  padding: 0.25rem 0.75rem;
  background: #dbeafe;
  color: #1e40af;
  border-radius: 9999px;
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: capitalize;
}

.no-po {
  color: #64748b;
  font-size: 0.938rem;
  margin-bottom: 1rem;
}

.modal-footer {
  padding-top: 1.5rem;
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
  background: #0f172a;
  border: 1px solid transparent;
  border-radius: 8px;
  font-weight: 500;
  font-size: 0.875rem;
  color: white;
  cursor: pointer;
  transition: all 0.15s ease;
  font-family: inherit;
}

.btn-primary:hover {
  background: #1e293b;
}

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
