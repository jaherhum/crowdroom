import { ref, computed, unref, watch } from 'vue';

/**
 * Client-side pagination over a reactive list.
 *
 * @param {import('vue').Ref<Array>|import('vue').ComputedRef<Array>} itemsRef
 *   Reactive array to paginate.
 * @param {number} pageSize Items per page.
 * @returns Pagination state and navigation helpers.
 */
export function usePagination(itemsRef, pageSize = 12) {
  const currentPage = ref(1);

  const totalPages = computed(() => Math.max(1, Math.ceil(unref(itemsRef).length / pageSize)));

  const pagedItems = computed(() => {
    const start = (currentPage.value - 1) * pageSize;
    return unref(itemsRef).slice(start, start + pageSize);
  });

  const hasPrev = computed(() => currentPage.value > 1);
  const hasNext = computed(() => currentPage.value < totalPages.value);

  function goToPage(page) {
    currentPage.value = Math.min(Math.max(1, page), totalPages.value);
  }

  function nextPage() {
    goToPage(currentPage.value + 1);
  }

  function prevPage() {
    goToPage(currentPage.value - 1);
  }

  // When the underlying list changes (e.g. after creating/leaving a room) the
  // current page may fall past the end. Clamp it back into range instead of
  // stranding the user on an empty page.
  watch(totalPages, (pages) => {
    if (currentPage.value > pages) currentPage.value = pages;
  });

  return {
    currentPage,
    totalPages,
    pageSize,
    pagedItems,
    hasPrev,
    hasNext,
    goToPage,
    nextPage,
    prevPage,
  };
}
