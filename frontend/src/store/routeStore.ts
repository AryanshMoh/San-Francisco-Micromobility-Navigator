import { create } from 'zustand';
import { Coordinate, Route, RoutePreferences, RouteProfile } from '../types';

interface RouteState {
  origin: Coordinate | null;
  destination: Coordinate | null;
  preferences: RoutePreferences;
  route: Route | null;
  alternatives: Route[];
  isCalculating: boolean;
  error: string | null;

  // Actions
  setOrigin: (coord: Coordinate | null) => void;
  setDestination: (coord: Coordinate | null) => void;
  swapLocations: () => void;
  setPreferences: (prefs: Partial<RoutePreferences>) => void;
  setRoute: (route: Route | null) => void;
  setAlternatives: (routes: Route[]) => void;
  setCalculating: (isCalc: boolean) => void;
  setError: (error: string | null) => void;
  clearRoute: () => void;
  reset: () => void;
}

const defaultPreferences: RoutePreferences = {
  profile: 'balanced',
  avoidHills: false,
  maxGradePercent: 15,
  preferBikeLanes: true,
  bikeLaneWeight: 0.7,
};

export const useRouteStore = create<RouteState>((set) => ({
  origin: null,
  destination: null,
  preferences: defaultPreferences,
  route: null,
  alternatives: [],
  isCalculating: false,
  error: null,

  setOrigin: (coord) => set({ origin: coord, error: null }),

  setDestination: (coord) => set({ destination: coord, error: null }),

  swapLocations: () =>
    set((state) => ({
      origin: state.destination,
      destination: state.origin,
    })),

  setPreferences: (prefs) =>
    set((state) => ({
      preferences: { ...state.preferences, ...prefs },
    })),

  setRoute: (route) => set({ route, error: null }),

  setAlternatives: (routes) => set({ alternatives: routes }),

  setCalculating: (isCalc) => set({ isCalculating: isCalc }),

  setError: (error) => set({ error, isCalculating: false }),

  clearRoute: () => set({ route: null, alternatives: [], error: null }),

  reset: () =>
    set({
      origin: null,
      destination: null,
      preferences: defaultPreferences,
      route: null,
      alternatives: [],
      isCalculating: false,
      error: null,
    }),
}));
