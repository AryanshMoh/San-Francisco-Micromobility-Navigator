import { create } from 'zustand';

interface MapState {
  // View state
  viewState: {
    longitude: number;
    latitude: number;
    zoom: number;
    pitch: number;
    bearing: number;
  };

  // Layer visibility
  showBikeLanes: boolean;
  showRiskZones: boolean;
  showTraffic: boolean;

  // Interaction state
  isFollowingUser: boolean;
  selectedRiskZoneId: string | null;

  // Actions
  setViewState: (viewState: Partial<MapState['viewState']>) => void;
  setShowBikeLanes: (show: boolean) => void;
  setShowRiskZones: (show: boolean) => void;
  setShowTraffic: (show: boolean) => void;
  setFollowingUser: (follow: boolean) => void;
  setSelectedRiskZone: (id: string | null) => void;
  flyTo: (longitude: number, latitude: number, zoom?: number) => void;
}

// San Francisco default view
const SF_CENTER = {
  longitude: -122.4194,
  latitude: 37.7749,
  zoom: 13,
  pitch: 0,
  bearing: 0,
};

export const useMapStore = create<MapState>((set) => ({
  viewState: SF_CENTER,
  showBikeLanes: false,
  showRiskZones: false,
  showTraffic: false,
  isFollowingUser: false,
  selectedRiskZoneId: null,

  setViewState: (newState) =>
    set((state) => ({
      viewState: { ...state.viewState, ...newState },
    })),

  setShowBikeLanes: (show) => set({ showBikeLanes: show }),

  setShowRiskZones: (show) => set({ showRiskZones: show }),

  setShowTraffic: (show) => set({ showTraffic: show }),

  setFollowingUser: (follow) => set({ isFollowingUser: follow }),

  setSelectedRiskZone: (id) => set({ selectedRiskZoneId: id }),

  flyTo: (longitude, latitude, zoom = 15) =>
    set((state) => ({
      viewState: {
        ...state.viewState,
        longitude,
        latitude,
        zoom,
      },
    })),
}));
