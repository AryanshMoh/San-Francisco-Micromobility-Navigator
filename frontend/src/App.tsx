import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Component, ErrorInfo, ReactNode, useCallback, useEffect, useRef, useState } from 'react';
import MapContainer from './components/map/MapContainer';
import SearchPanel from './components/routing/SearchPanel';
import RoutePanel from './components/routing/RoutePanel';
import { NavigationView } from './components/navigation';
import { useRouteStore } from './store/routeStore';
import { useNavigationStore } from './store/navigationStore';
import IntroScreen from './components/intro/IntroScreen';
import ImmersiveLanding from './components/intro/ImmersiveLanding';

const MAP_TRANSITION_DURATION_MS = 1300;
type IntroStage = 'intro' | 'immersive' | 'transitioning' | 'map';

// Error boundary to catch rendering errors
interface ErrorBoundaryState {
  hasError: boolean;
  error: Error | null;
}

class ErrorBoundary extends Component<{ children: ReactNode }, ErrorBoundaryState> {
  constructor(props: { children: ReactNode }) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error('[ErrorBoundary] Caught error:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="h-screen w-screen flex items-center justify-center bg-slate-100 p-4">
          <div className="bg-white p-6 rounded-xl shadow-lg max-w-md">
            <h2 className="text-lg font-semibold text-red-600 mb-2">Something went wrong</h2>
            <p className="text-sm text-slate-600 mb-4">{this.state.error?.message}</p>
            <pre className="text-xs bg-slate-100 p-3 rounded overflow-auto max-h-40 mb-4">
              {this.state.error?.stack}
            </pre>
            <button
              onClick={() => {
                this.setState({ hasError: false, error: null });
                window.location.reload();
              }}
              className="px-4 py-2 bg-slate-900 text-white rounded-lg text-sm"
            >
              Reload Page
            </button>
          </div>
        </div>
      );
    }

    return this.props.children;
  }
}

function HomePage() {
  const { route } = useRouteStore();
  const { isActive: isNavigating } = useNavigationStore();

  return (
    <div className="h-full w-full relative">
      <MapContainer />

      {/* Show search/route panels only when NOT navigating */}
      {!isNavigating && (
        <>
          <SearchPanel />
          {route && <RoutePanel />}
        </>
      )}

      {/* Show navigation UI when actively navigating */}
      {isNavigating && <NavigationView />}
    </div>
  );
}

function IntroGate() {
  const [stage, setStage] = useState<IntroStage>('intro');
  const transitionTimerRef = useRef<number | undefined>(undefined);

  const handleEnterSite = useCallback(() => {
    setStage('immersive');
  }, []);

  const handleNavigateToMap = useCallback(() => {
    setStage((currentStage) => {
      if (currentStage !== 'immersive') {
        return currentStage;
      }

      transitionTimerRef.current = window.setTimeout(() => {
        setStage('map');
      }, MAP_TRANSITION_DURATION_MS);
      return 'transitioning';
    });
  }, []);

  useEffect(() => {
    return () => {
      window.clearTimeout(transitionTimerRef.current);
    };
  }, []);

  return (
    <div className={`experience-gate experience-gate--${stage}`}>
      {(stage === 'transitioning' || stage === 'map') && (
        <div className={`experience-gate__map-layer${stage === 'map' ? ' experience-gate__map-layer--visible' : ''}`}>
          <HomePage />
        </div>
      )}

      {stage === 'intro' && <IntroScreen onEnter={handleEnterSite} />}

      {(stage === 'immersive' || stage === 'transitioning') && (
        <ImmersiveLanding
          onNavigate={handleNavigateToMap}
          isExiting={stage === 'transitioning'}
        />
      )}

      {stage === 'transitioning' && (
        <div className="experience-gate__transition-curtain" aria-hidden="true" />
      )}
    </div>
  );
}

function App() {
  return (
    <ErrorBoundary>
      <BrowserRouter>
        <div className="h-screen w-screen overflow-hidden">
          <Routes>
            <Route path="/" element={<IntroGate />} />
          </Routes>
        </div>
      </BrowserRouter>
    </ErrorBoundary>
  );
}

export default App;
