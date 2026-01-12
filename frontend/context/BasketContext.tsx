import React, {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
} from "react";

import type { Ad } from "@/types/ad";

type BasketContextValue = {
  items: Ad[];
  addToBasket: (item: Ad) => void;
  removeFromBasket: (index: number) => void;
  clearBasket: () => void;
  isInBasket: (item: Ad) => boolean;
};

function getAdKey(item: Ad) {
  return [
    item.product?.toLowerCase() ?? "",
    item.store?.toLowerCase() ?? "",
    String(item.price ?? ""),
    item.date ?? "",
    item.image_filename ?? "",
  ].join("|");
}

const BasketContext = createContext<BasketContextValue | undefined>(undefined);

export function BasketProvider({ children }: { children: React.ReactNode }) {
  const [items, setItems] = useState<Ad[]>([]);

  const addToBasket = useCallback((item: Ad) => {
    setItems((prev) => {
      const exists = prev.some(
        (existing) => getAdKey(existing) === getAdKey(item)
      );
      return exists ? prev : [...prev, item];
    });
  }, []);

  const removeFromBasket = useCallback((index: number) => {
    setItems((prev) => prev.filter((_, idx) => idx !== index));
  }, []);

  const clearBasket = useCallback(() => {
    setItems([]);
  }, []);

  const isInBasket = useCallback(
    (item: Ad) =>
      items.some((existing) => getAdKey(existing) === getAdKey(item)),
    [items]
  );

  const value = useMemo(
    () => ({ items, addToBasket, removeFromBasket, clearBasket, isInBasket }),
    [items, addToBasket, removeFromBasket, clearBasket, isInBasket]
  );

  return (
    <BasketContext.Provider value={value}>{children}</BasketContext.Provider>
  );
}

export function useBasket() {
  const context = useContext(BasketContext);
  if (!context) {
    throw new Error("useBasket must be used within a BasketProvider");
  }
  return context;
}
