import React, { useEffect, useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  FlatList,
  TouchableOpacity,
  Image,
  ActivityIndicator,
  Alert
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { Ionicons } from '@expo/vector-icons';
import AsyncStorage from '@react-native-async-storage/async-storage';
import axios from 'axios';
import { useRouter, useLocalSearchParams } from 'expo-router';

const EXPO_PUBLIC_BACKEND_URL = process.env.EXPO_PUBLIC_BACKEND_URL;

interface Song {
  id: string;
  title: string;
  artist: string;
  duration: number;
  file_data: string;
  cover_art?: string;
  genre?: string;
  created_at: string;
  uploaded_by: string;
}

interface Playlist {
  id: string;
  title: string;
  description?: string;
  songs: string[];
  cover_art?: string;
  created_by: string;
  created_at: string;
  is_public: boolean;
}

export default function PlaylistScreen() {
  const { id } = useLocalSearchParams();
  const [playlist, setPlaylist] = useState<Playlist | null>(null);
  const [songs, setSongs] = useState<Song[]>([]);
  const [loading, setLoading] = useState(true);
  const [currentSong, setCurrentSong] = useState<Song | null>(null);
  const [isPlaying, setIsPlaying] = useState(false);
  const router = useRouter();

  useEffect(() => {
    if (id) {
      loadPlaylistData();
    }
  }, [id]);

  const loadPlaylistData = async () => {
    try {
      const token = await AsyncStorage.getItem('access_token');
      if (!token) {
        router.replace('/');
        return;
      }

      // Load playlist info and songs
      const [playlistResponse, songsResponse] = await Promise.all([
        axios.get(`${EXPO_PUBLIC_BACKEND_URL}/api/playlists`, {
          headers: { Authorization: `Bearer ${token}` }
        }),
        axios.get(`${EXPO_PUBLIC_BACKEND_URL}/api/playlists/${id}/songs`, {
          headers: { Authorization: `Bearer ${token}` }
        })
      ]);

      // Find the specific playlist
      const foundPlaylist = playlistResponse.data.find((p: Playlist) => p.id === id);
      setPlaylist(foundPlaylist);
      setSongs(songsResponse.data);
    } catch (error: any) {
      console.error('Error loading playlist:', error);
      if (error.response?.status === 401) {
        await AsyncStorage.clear();
        router.replace('/');
      } else {
        Alert.alert('Error', 'Failed to load playlist');
      }
    } finally {
      setLoading(false);
    }
  };

  const formatDuration = (seconds: number) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins}:${secs.toString().padStart(2, '0')}`;
  };

  const handleSongPress = (song: Song) => {
    setCurrentSong(song);
    setIsPlaying(true);
    // Navigate to player screen
    router.push(`/player/${song.id}`);
  };

  const renderSongItem = ({ item, index }: { item: Song; index: number }) => (
    <TouchableOpacity
      style={styles.songItem}
      onPress={() => handleSongPress(item)}
    >
      <View style={styles.songIndex}>
        <Text style={styles.songIndexText}>{index + 1}</Text>
      </View>
      <Image
        source={{ uri: item.cover_art || 'https://via.placeholder.com/150' }}
        style={styles.songCover}
      />
      <View style={styles.songInfo}>
        <Text style={styles.songTitle} numberOfLines={1}>{item.title}</Text>
        <Text style={styles.songArtist} numberOfLines={1}>{item.artist}</Text>
      </View>
      <Text style={styles.songDuration}>{formatDuration(item.duration)}</Text>
      <TouchableOpacity style={styles.songMenuButton}>
        <Ionicons name="ellipsis-vertical" size={20} color="#9CA3AF" />
      </TouchableOpacity>
    </TouchableOpacity>
  );

  if (loading) {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color="#3B82F6" />
          <Text style={styles.loadingText}>Loading playlist...</Text>
        </View>
      </SafeAreaView>
    );
  }

  if (!playlist) {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.errorContainer}>
          <Text style={styles.errorText}>Playlist not found</Text>
          <TouchableOpacity style={styles.backButton} onPress={() => router.back()}>
            <Text style={styles.backButtonText}>Go Back</Text>
          </TouchableOpacity>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()} style={styles.backButton}>
          <Ionicons name="chevron-back" size={24} color="#ffffff" />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>Playlist</Text>
        <TouchableOpacity style={styles.menuButton}>
          <Ionicons name="ellipsis-vertical" size={24} color="#ffffff" />
        </TouchableOpacity>
      </View>

      {/* Playlist Info */}
      <View style={styles.playlistHeader}>
        <Image
          source={{ uri: playlist.cover_art || 'https://via.placeholder.com/200' }}
          style={styles.playlistCover}
        />
        <Text style={styles.playlistTitle}>{playlist.title}</Text>
        <Text style={styles.playlistDescription}>
          {playlist.description || `${songs.length} songs`}
        </Text>
        
        {/* Play Controls */}
        <View style={styles.playControls}>
          <TouchableOpacity style={styles.shuffleButton}>
            <Ionicons name="shuffle" size={20} color="#ffffff" />
          </TouchableOpacity>
          <TouchableOpacity style={styles.playButton}>
            <Ionicons name="play" size={32} color="#ffffff" />
          </TouchableOpacity>
          <TouchableOpacity style={styles.downloadButton}>
            <Ionicons name="download" size={20} color="#ffffff" />
          </TouchableOpacity>
        </View>
      </View>

      {/* Songs List */}
      <FlatList
        data={songs}
        renderItem={renderSongItem}
        keyExtractor={(item) => item.id}
        style={styles.songsList}
        showsVerticalScrollIndicator={false}
        ListEmptyComponent={
          <View style={styles.emptyContainer}>
            <Text style={styles.emptyText}>No songs in this playlist</Text>
            <TouchableOpacity style={styles.addSongButton}>
              <Text style={styles.addSongButtonText}>Add Songs</Text>
            </TouchableOpacity>
          </View>
        }
      />
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#1F2937',
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  loadingText: {
    color: '#ffffff',
    marginTop: 16,
    fontSize: 16,
  },
  errorContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  errorText: {
    color: '#ffffff',
    fontSize: 18,
    marginBottom: 16,
  },
  header: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingHorizontal: 24,
    paddingVertical: 16,
  },
  backButton: {
    padding: 8,
  },
  headerTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#ffffff',
  },
  menuButton: {
    padding: 8,
  },
  playlistHeader: {
    alignItems: 'center',
    paddingHorizontal: 24,
    paddingBottom: 24,
  },
  playlistCover: {
    width: 200,
    height: 200,
    borderRadius: 12,
    marginBottom: 16,
  },
  playlistTitle: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#ffffff',
    marginBottom: 8,
    textAlign: 'center',
  },
  playlistDescription: {
    fontSize: 16,
    color: '#9CA3AF',
    marginBottom: 24,
    textAlign: 'center',
  },
  playControls: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 32,
  },
  shuffleButton: {
    width: 48,
    height: 48,
    borderRadius: 24,
    backgroundColor: '#374151',
    alignItems: 'center',
    justifyContent: 'center',
  },
  playButton: {
    width: 64,
    height: 64,
    borderRadius: 32,
    backgroundColor: '#3B82F6',
    alignItems: 'center',
    justifyContent: 'center',
  },
  downloadButton: {
    width: 48,
    height: 48,
    borderRadius: 24,
    backgroundColor: '#374151',
    alignItems: 'center',
    justifyContent: 'center',
  },
  songsList: {
    flex: 1,
    paddingHorizontal: 24,
  },
  songItem: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#374151',
  },
  songIndex: {
    width: 24,
    alignItems: 'center',
    marginRight: 16,
  },
  songIndexText: {
    color: '#9CA3AF',
    fontSize: 14,
  },
  songCover: {
    width: 48,
    height: 48,
    borderRadius: 8,
    marginRight: 16,
  },
  songInfo: {
    flex: 1,
  },
  songTitle: {
    fontSize: 16,
    fontWeight: '500',
    color: '#ffffff',
    marginBottom: 4,
  },
  songArtist: {
    fontSize: 14,
    color: '#9CA3AF',
  },
  songDuration: {
    fontSize: 14,
    color: '#9CA3AF',
    marginRight: 12,
  },
  songMenuButton: {
    padding: 8,
  },
  emptyContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingVertical: 64,
  },
  emptyText: {
    color: '#9CA3AF',
    fontSize: 16,
    marginBottom: 16,
  },
  addSongButton: {
    backgroundColor: '#3B82F6',
    paddingHorizontal: 24,
    paddingVertical: 12,
    borderRadius: 8,
  },
  addSongButtonText: {
    color: '#ffffff',
    fontWeight: '500',
  },
  backButtonText: {
    color: '#3B82F6',
    fontWeight: '500',
  },
});
