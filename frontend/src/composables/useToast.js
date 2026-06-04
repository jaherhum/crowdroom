import { ref } from 'vue';

const toasts = ref([]);
let nextId = 0;

export function useToast() {
  function showToast(message, type = 'error') {
    const id = nextId++;
    toasts.value.push({ id, message, type });
    setTimeout(() => {
      toasts.value = toasts.value.filter((toast) => toast.id !== id);
    }, 4000);
  }

  return { toasts, showToast };
}
