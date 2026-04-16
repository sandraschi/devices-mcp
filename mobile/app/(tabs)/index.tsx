import React from 'react';
import { StyleSheet, FlatList, ActivityIndicator, TouchableOpacity, View } from 'react-native';
import { MaterialCommunityIcons } from '@expo/vector-icons';

import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { useFleet, FleetNode } from '@/hooks/useFleet';

export default function FleetDashboardScreen() {
  const { nodes, loading, error, refresh } = useFleet();

  const renderNode = ({ item }: { item: FleetNode }) => {
    const statusColor = item.status === 'online' ? '#4CAF50' : item.status === 'offline' ? '#f44336' : '#FFC107';
    const lastSeen = new Date(item.last_heartbeat * 1000).toLocaleTimeString();

    return (
      <Link href={{ pathname: '/node/[id]', params: { id: item.node_id } }} asChild>
        <TouchableOpacity style={styles.card}>
          <View style={styles.cardHeader}>
            <ThemedText type="subtitle">{item.node_id}</ThemedText>
            <View style={[styles.statusBadge, { backgroundColor: statusColor }]}>
              <ThemedText style={styles.statusText}>{item.status.toUpperCase()}</ThemedText>
            </View>
          </View>
          
          <View style={styles.cardBody}>
            <View style={styles.infoRow}>
              <MaterialCommunityIcons name="ip-network" size={16} color="#888" />
              <ThemedText style={styles.infoText}>{item.ip_address}</ThemedText>
            </View>
            <View style={styles.infoRow}>
              <MaterialCommunityIcons name="clock-outline" size={16} color="#888" />
              <ThemedText style={styles.infoText}>Last seen: {lastSeen}</ThemedText>
            </View>
            <View style={styles.infoRow}>
              <MaterialCommunityIcons name="trending-up" size={16} color="#888" />
              <ThemedText style={styles.infoText}>Drift: {item.drift_score.toFixed(2)}</ThemedText>
            </View>
          </View>
        </TouchableOpacity>
      </Link>
    );
  };

  if (loading && nodes.length === 0) {
    return (
      <ThemedView style={styles.centered}>
        <ActivityIndicator size="large" color="#A1CEDC" />
        <ThemedText>Scanning Fleet Hub...</ThemedText>
      </ThemedView>
    );
  }

  if (error && nodes.length === 0) {
    return (
      <ThemedView style={styles.centered}>
        <MaterialCommunityIcons name="alert-circle-outline" size={48} color="#f44336" />
        <ThemedText style={styles.errorText}>{error}</ThemedText>
        <TouchableOpacity style={styles.retryButton} onPress={refresh}>
          <ThemedText style={styles.retryButtonText}>RETRY CONNECTION</ThemedText>
        </TouchableOpacity>
      </ThemedView>
    );
  }

  return (
    <ThemedView style={styles.container}>
      <View style={styles.header}>
        <ThemedText type="title">Fleet Supervisor</ThemedText>
        <TouchableOpacity onPress={refresh}>
          <MaterialCommunityIcons name="refresh" size={24} color="#A1CEDC" />
        </TouchableOpacity>
      </View>

      <FlatList
        data={nodes}
        renderItem={renderNode}
        keyExtractor={(item) => item.node_id}
        contentContainerStyle={styles.list}
        ListEmptyComponent={
          <ThemedView style={styles.empty}>
            <ThemedText>No nodes reported in yet.</ThemedText>
          </ThemedView>
        }
      />
    </ThemedView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    paddingTop: 60,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 20,
    marginBottom: 20,
  },
  list: {
    paddingHorizontal: 16,
    paddingBottom: 20,
  },
  card: {
    backgroundColor: 'rgba(255,255,255,0.05)',
    borderRadius: 12,
    padding: 16,
    marginBottom: 12,
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.1)',
  },
  cardHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 12,
  },
  statusBadge: {
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 6,
  },
  statusText: {
    fontSize: 10,
    fontWeight: 'bold',
    color: '#000',
  },
  cardBody: {
    gap: 6,
  },
  infoRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  infoText: {
    fontSize: 13,
    color: '#888',
  },
  centered: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    gap: 12,
  },
  errorText: {
    color: '#f44336',
    textAlign: 'center',
    paddingHorizontal: 40,
  },
  retryButton: {
    backgroundColor: '#1D3D47',
    padding: 12,
    borderRadius: 8,
    marginTop: 10,
  },
  retryButtonText: {
    color: '#fff',
    fontWeight: 'bold',
  },
  empty: {
    padding: 40,
    alignItems: 'center',
  }
});
