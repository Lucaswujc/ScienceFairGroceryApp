import { Image } from "expo-image";
import React, { useMemo } from "react";
import { Button, FlatList, StyleSheet, Text, View } from "react-native";

import { Collapsible } from "@/components/Collapsible";
import { ThemedText } from "@/components/ThemedText";
import { ThemedView } from "@/components/ThemedView";
import { useBasket } from "@/context/BasketContext";
import type { Ad } from "@/types/ad";

function priceToNumber(price: string | number) {
  if (typeof price === "number") {
    return price;
  }
  const trimmed = price.trim().replace(/,/g, "");
  const dealMatch = trimmed.match(/^[0-9]+\s*\/\s*\$?([0-9]+(?:\.[0-9]+)?)/i);
  if (dealMatch) {
    const dealTotal = parseFloat(dealMatch[1]);
    return Number.isNaN(dealTotal) ? 0 : dealTotal;
  }
  const match = trimmed.match(/^\$?\d+(?:\.\d+)?/);
  if (!match) {
    return 0;
  }
  const numeric = parseFloat(match[0].replace(/^\$/, ""));
  return Number.isNaN(numeric) ? 0 : numeric;
}

type StoreEntry = {
  item: Ad;
  index: number;
};

type StoreGroup = {
  store: string;
  entries: StoreEntry[];
  subtotal: number;
};

export default function CartScreen() {
  const { items, removeFromBasket, clearBasket } = useBasket();

  const total = useMemo(() => {
    return items.reduce((sum, item) => sum + priceToNumber(item.price), 0);
  }, [items]);

  const storeGroups = useMemo<StoreGroup[]>(() => {
    const map = new Map<string, StoreEntry[]>();
    items.forEach((item, index) => {
      const store = item.store ?? "Unknown store";
      const list = map.get(store) ?? [];
      list.push({ item, index });
      map.set(store, list);
    });

    return Array.from(map.entries()).map(([store, entries]) => ({
      store,
      entries,
      subtotal: entries.reduce(
        (sum, entry) => sum + priceToNumber(entry.item.price),
        0
      ),
    }));
  }, [items]);

  const renderEntry = ({ item, index }: StoreEntry) => {
    const uri =
      item.image_uri ??
      (item.image_base64
        ? `data:image/png;base64,${item.image_base64}`
        : undefined);

    return (
      <View style={styles.itemRow}>
        {uri ? (
          <Image source={{ uri }} style={styles.itemImage} contentFit="cover" />
        ) : (
          <View style={[styles.itemImage, styles.noImage]}>
            <Text>No image</Text>
          </View>
        )}
        <View style={styles.itemDetail}>
          <ThemedText type="defaultSemiBold">{item.product}</ThemedText>
          <ThemedText>
            {item.store ?? "Unknown store"} — {item.date ?? ""}
          </ThemedText>
          <ThemedText>{String(item.price)}</ThemedText>
        </View>
        <Button
          title="Remove"
          onPress={() => removeFromBasket(index)}
          color="#c62828"
        />
      </View>
    );
  };

  const renderGroup = ({ item }: { item: StoreGroup }) => (
    <View style={styles.groupContainer}>
      <Collapsible
        title={`${item.store} • ${item.entries.length} item${
          item.entries.length === 1 ? "" : "s"
        } • $${item.subtotal.toFixed(2)}`}
      >
        {item.entries.map((entry, idx) => (
          <View key={`${entry.item.product}-${entry.index}`}>
            {renderEntry(entry)}
            {idx < item.entries.length - 1 && <View style={styles.separator} />}
          </View>
        ))}
      </Collapsible>
    </View>
  );

  return (
    <ThemedView style={styles.container}>
      <ThemedText type="title">Cart</ThemedText>
      <View style={styles.summary}>
        <ThemedText type="subtitle">{items.length} item(s)</ThemedText>
        <ThemedText type="subtitle">
          Estimated total: ${total.toFixed(2)}
        </ThemedText>
        {items.length > 0 && (
          <Button title="Clear Cart" onPress={clearBasket} color="#444" />
        )}
      </View>

      {items.length === 0 ? (
        <View style={styles.emptyState}>
          <ThemedText>Add items from the Ads tab to see them here.</ThemedText>
        </View>
      ) : (
        <FlatList
          data={storeGroups}
          style={styles.list}
          contentContainerStyle={styles.groupsContent}
          keyExtractor={(group) => group.store}
          renderItem={renderGroup}
          ItemSeparatorComponent={() => <View style={styles.groupSpacer} />}
        />
      )}
    </ThemedView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    padding: 12,
  },
  summary: {
    gap: 8,
    marginBottom: 16,
  },
  list: {
    flex: 1,
  },
  groupsContent: {
    paddingBottom: 24,
  },
  groupContainer: {
    borderWidth: 1,
    borderColor: "#e0e0e0",
    borderRadius: 12,
    padding: 12,
  },
  groupSpacer: {
    height: 12,
  },
  itemRow: {
    flexDirection: "row",
    alignItems: "center",
    paddingVertical: 10,
    paddingRight: 8,
  },
  itemImage: {
    width: 72,
    height: 72,
    borderRadius: 8,
  },
  noImage: {
    backgroundColor: "#eee",
    alignItems: "center",
    justifyContent: "center",
  },
  itemDetail: {
    marginLeft: 12,
    flex: 1,
  },
  separator: {
    height: 1,
    backgroundColor: "#e0e0e0",
  },
  emptyState: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
  },
});
