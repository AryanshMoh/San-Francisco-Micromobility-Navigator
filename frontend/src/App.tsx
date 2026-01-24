import { useState } from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import MapContainer from './components/map/MapContainer';
import SearchPanel from './components/routing/SearchPanel';
import RoutePanel from './components/routing/RoutePanel';
import { useRouteStore } from './store/routeStore';

function HomePage() {
  const { route } = useRouteStore();

  return (
    <div className="h-full w-full relative">
      <MapContainer />
      <SearchPanel />
      {route && <RoutePanel />}
    </div>
  );
}

function App() {
  return (
    <BrowserRouter>
      <div className="h-screen w-screen overflow-hidden">
        <Routes>
          <Route path="/" element={<HomePage />} />
        </Routes>
      </div>
    </BrowserRouter>
  );
}

export default App;
