import React from 'react';
import { StyleSheet, ScrollView, View, TouchableOpacity, Share } from 'react-native';
import { useLocalSearchParams, Stack, router } from 'expo-router';
import { MaterialCommunityIcons } from '@expo/vector-icons';

import { ThemedText } from '@/components/themed-text';
import { ThemedView } from '@/components/themed-view';
import { useFleet } from '@/hooks/useFleet';

export default function NodeDetailScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const { nodes } = useFleet();
  
  const node = nodes.find(n => n.node_id === id);

  const onAnnotate = async () => {
    // Stub for the 'Annotator' feature mentioned in the AI chat
    const message = `[LOOK-SEE] Node: ${id}\nStatus: ${node?.status}\nDrift: ${node?.drift_score.toFixed(2)}\n\nRequest: "Please investigate this node's performance."`;
    
    try {
      await Share.share({
        message,
        title: `Look-See Annotation: ${id}`,
      });
    } catch (error) {
      console.error(error);
    }
  };

  if (!node) {
    return (
      <ThemedView style={styles.centered}>
        <ThemedText>Node not found</ThemedText>
        <TouchableOpacity onPress={() => router.back()}>
          <ThemedText style={{ color: '#A1CEDC', marginTop: 10 }}>Go Back</ThemedText>
        </TouchableOpacity>
      </ThemedView>
    );
  }

  const statusColor = node.status === 'online' ? '#4CAF50' : node.status === 'offline' ? '#f44336' : '#FFC107';

  return (
    <ThemedView style={styles.container}>
      <Stack.Screen options={{ title: node.node_id, headerShown: true }} />
      
      <ScrollView contentContainerStyle={styles.scroll}>
        <View style={styles.header}>
          <View style={[styles.statusCircle, { backgroundColor: statusColor }]} />
          <ThemedText type="title">{node.node_id}</ThemedText>
        </View>

        <ThemedView style={styles.section}>
          <ThemedText type="defaultSemiBold">Status Overview</ThemedText>
          <View style={styles.statsRow}>
            <View style={styles.stat}>
              <ThemedText style={styles.statValue}>{node.status.toUpperCase()}</ThemedText>
              <ThemedText style={styles.statLabel}>STATUS</ThemedText>
            </View>
            <View style={styles.stat}>
              <ThemedText style={styles.statValue}>{node.drift_score.toFixed(3)}</ThemedText>
              <ThemedText style={styles.statLabel}>DRIFT</ThemedText>
            </View>
          </View>
        </ThemedView>

        <ThemedView style={styles.section}>
          <ThemedText type="defaultSemiBold">Connectivity</ThemedText>
          <View style={styles.infoRow}>
            <MaterialCommunityIcons name="ip-network" size={20} color="#888" />
            <ThemedText style={styles.infoText}>{node.ip_address}</ThemedText>
          </View>
          <View style={styles.infoRow}>
            <MaterialCommunityIcons name="clock-outline" size={20} color="#888" />
            <ThemedText style={styles.infoText}>
              Last Heartbeat: {new Date(node.last_heartbeat * 1000).toLocaleString()}
            </ThemedText>
          </View>
        </ThemedView>

        <ThemedView style={styles.section}>
          <ThemedText type="defaultSemiBold">Supervisor Actions</ThemedText>
          <TouchableOpacity style={styles.actionButton} onPress={onAnnotate}>
            <MaterialCommunityIcons name="comment-edit-outline" size={24} color="#fff" />
            <ThemedText style={styles.actionButtonText}>Take Look-See Clip</ThemedText>
          </TouchableOpacity>
          <TouchableOpacity style={[styles.actionButton, { backgroundColor: '#333', marginTop: 10 }]}>
            <MaterialCommunityIcons name="restart" size={24} color="#fff" />
            <ThemedText style={styles.actionButtonText}>Request Remote Reboot</ThemedText>
          </TouchableOpacity>
        </ThemedView>
      </ScrollView>
    </ThemedView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  scroll: {
    padding: 20,
    gap: 20,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    marginBottom: 10,
  },
  statusCircle: {
    width: 24,
    height: 24,
    borderRadius: 12,
  },
  section: {
    backgroundColor: 'rgba(255,255,255,0.05)',
    borderRadius: 16,
    padding: 16,
    gap: 12,
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.1)',
  },
  statsRow: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    marginTop: 10,
  },
  stat: {
    alignItems: 'center',
  },
  statValue: {
    fontSize: 20,
    fontWeight: 'bold',
  },
  statLabel: {
    fontSize: 10,
    color: '#888',
    marginTop: 4,
  },
  infoRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
  },
  infoText: {
    fontSize: 14,
    color: '#ccc',
  },
  centered: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  actionButton: {
    backgroundColor: '#1D3D47',
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 14,
    borderRadius: 12,
    gap: 10,
  },
  actionButtonText: {
    color: '#fff',
    fontWeight: 'bold',
  }
});
