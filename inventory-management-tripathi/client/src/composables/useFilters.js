import { ref, computed } from 'vue'

// Shared filter state (singleton pattern)
const selectedPeriod = ref('all')
const selectedLocation = ref('all')
const selectedCategory = ref('all')
const selectedStatus = ref('all')

export function useFilters() {
  // Check if any filters are active
  const hasActiveFilters = computed(() => {
    return selectedPeriod.value !== 'all' ||
           selectedLocation.value !== 'all' ||
           selectedCategory.value !== 'all' ||
           selectedStatus.value !== 'all'
  })

  // Reset all filters to default
  const resetFilters = () => {
    selectedPeriod.value = 'all'
    selectedLocation.value = 'all'
    selectedCategory.value = 'all'
    selectedStatus.value = 'all'
  }

  // Get current filters as an object for API calls
  const getCurrentFilters = () => {
    const filters = {
      warehouse: selectedLocation.value,
      category: selectedCategory.value,
      status: selectedStatus.value
    }

    // Map period to month format for API
    if (selectedPeriod.value !== 'all') {
      filters.month = selectedPeriod.value
    }

    return filters
  }

  return {
    // State
    selectedPeriod,
    selectedLocation,
    selectedCategory,
    selectedStatus,

    // Computed
    hasActiveFilters,

    // Methods
    resetFilters,
    getCurrentFilters
  }
}
