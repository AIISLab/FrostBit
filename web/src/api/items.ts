import { apiGet, apiPost } from "./client";

export interface Item {
  id: number;
  name: string;
  description?: string | null;
}

export interface ItemCreate {
  name: string;
  description?: string | null;
}

export const fetchItems = () => apiGet<Item[]>("/items");
export const createItem = (payload: ItemCreate) => apiPost<Item>("/items", payload);
