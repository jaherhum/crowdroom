import { describe, it, expect } from 'vitest';
import { ref, nextTick } from 'vue';
import { usePagination } from './usePagination.js';

function makeItems(count) {
  return Array.from({ length: count }, (_, index) => index + 1);
}

describe('usePagination', () => {
  it('slices the first page', () => {
    const items = ref(makeItems(30));
    const { pagedItems, currentPage } = usePagination(items, 12);
    expect(currentPage.value).toBe(1);
    expect(pagedItems.value).toEqual(makeItems(12));
  });

  it('slices subsequent pages', () => {
    const items = ref(makeItems(30));
    const { pagedItems, goToPage } = usePagination(items, 12);
    goToPage(2);
    expect(pagedItems.value).toEqual(Array.from({ length: 12 }, (_, index) => index + 13));
    goToPage(3);
    expect(pagedItems.value).toEqual([25, 26, 27, 28, 29, 30]);
  });

  it('computes totalPages for exact multiples and remainders', () => {
    expect(usePagination(ref(makeItems(24)), 12).totalPages.value).toBe(2);
    expect(usePagination(ref(makeItems(25)), 12).totalPages.value).toBe(3);
  });

  it('clamps navigation at both bounds', () => {
    const items = ref(makeItems(30));
    const { currentPage, nextPage, prevPage, goToPage, hasPrev, hasNext } = usePagination(
      items,
      12,
    );
    prevPage();
    expect(currentPage.value).toBe(1);
    expect(hasPrev.value).toBe(false);
    goToPage(99);
    expect(currentPage.value).toBe(3);
    expect(hasNext.value).toBe(false);
    nextPage();
    expect(currentPage.value).toBe(3);
  });

  it('handles an empty list', () => {
    const { totalPages, pagedItems } = usePagination(ref([]), 12);
    expect(totalPages.value).toBe(1);
    expect(pagedItems.value).toEqual([]);
  });

  it('handles a single-page list', () => {
    const { totalPages, pagedItems } = usePagination(ref(makeItems(5)), 12);
    expect(totalPages.value).toBe(1);
    expect(pagedItems.value).toEqual(makeItems(5));
  });

  it('clamps currentPage back into range when the list shrinks', async () => {
    const items = ref(makeItems(30));
    const { currentPage, goToPage } = usePagination(items, 12);
    goToPage(3);
    expect(currentPage.value).toBe(3);
    items.value = makeItems(5);
    await nextTick();
    expect(currentPage.value).toBe(1);
  });
});
