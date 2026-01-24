import { useCallback } from 'react';
import { useMutation } from '@tanstack/react-query';
import { useRouteStore } from '../store/routeStore';
import { calculateRoute, getAlternativeRoutes } from '../api/routing';
import { RouteRequest } from '../types';

export function useRouting() {
  const {
    origin,
    destination,
    preferences,
    route,
    alternatives,
    isCalculating,
    error,
    setRoute,
    setAlternatives,
    setCalculating,
    setError,
    clearRoute,
  } = useRouteStore();

  const calculateMutation = useMutation({
    mutationFn: calculateRoute,
    onMutate: () => {
      setCalculating(true);
      setError(null);
    },
    onSuccess: (data) => {
      setRoute(data);
      setCalculating(false);
    },
    onError: (err: Error) => {
      setError(err.message);
      setCalculating(false);
    },
  });

  const alternativesMutation = useMutation({
    mutationFn: getAlternativeRoutes,
    onMutate: () => {
      setCalculating(true);
      setError(null);
    },
    onSuccess: (data) => {
      setAlternatives(data.routes);
      // Set the recommended route as the main route
      if (data.routes.length > 0) {
        setRoute(data.routes[data.comparison.recommendedIndex] || data.routes[0]);
      }
      setCalculating(false);
    },
    onError: (err: Error) => {
      setError(err.message);
      setCalculating(false);
    },
  });

  const calculate = useCallback(() => {
    if (!origin || !destination) {
      setError('Please set both origin and destination');
      return;
    }

    const request: RouteRequest = {
      origin,
      destination,
      vehicleType: 'scooter',
      preferences,
      avoidRiskZones: true,
    };

    calculateMutation.mutate(request);
  }, [origin, destination, preferences, calculateMutation, setError]);

  const calculateWithAlternatives = useCallback(() => {
    if (!origin || !destination) {
      setError('Please set both origin and destination');
      return;
    }

    const request: RouteRequest = {
      origin,
      destination,
      vehicleType: 'scooter',
      preferences,
      avoidRiskZones: true,
    };

    alternativesMutation.mutate(request);
  }, [origin, destination, preferences, alternativesMutation, setError]);

  const selectAlternative = useCallback(
    (index: number) => {
      if (alternatives[index]) {
        setRoute(alternatives[index]);
      }
    },
    [alternatives, setRoute]
  );

  return {
    origin,
    destination,
    preferences,
    route,
    alternatives,
    isCalculating,
    error,
    calculate,
    calculateWithAlternatives,
    selectAlternative,
    clearRoute,
  };
}
