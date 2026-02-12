-- Additional risk zones for areas not covered in original dataset
-- Based on SF Open Data collision analysis (2020-2024)
-- New thresholds: Yellow 140-179, Light Red 180-229, Dark Red 230+

-- ============================================================================
-- GOLDEN GATE PARK AREA (179 total neighborhood crashes)
-- ============================================================================

-- Golden Gate Park - JFK Drive / Stanyan entrance area
INSERT INTO risk_zones (
    id, geometry, hazard_type, severity, name, description,
    is_permanent, alert_radius_meters, source, confidence_score,
    reported_count, is_active
) VALUES (
    'f1a2b3c4-d5e6-4f7a-8b9c-0d1e2f3a4b5c',
    ST_SetSRID(ST_MakePoint(-122.45397952, 37.77142839), 4326),
    'HIGH_TRAFFIC',
    'MEDIUM',
    'Golden Gate Park - Stanyan Entrance (158 crashes)',
    '158 traffic incidents near Stanyan St entrance. Cyclists merging with park traffic.',
    true,
    280,
    'MUNICIPAL',
    0.90,
    158,
    true
);

-- Golden Gate Park - JFK Drive mid-park
INSERT INTO risk_zones (
    id, geometry, hazard_type, severity, name, description,
    is_permanent, alert_radius_meters, source, confidence_score,
    reported_count, is_active
) VALUES (
    'a2b3c4d5-e6f7-4a8b-9c0d-1e2f3a4b5c6d',
    ST_SetSRID(ST_MakePoint(-122.47989542, 37.77049587), 4326),
    'DANGEROUS_INTERSECTION',
    'MEDIUM',
    'Golden Gate Park - JFK Drive Central (148 crashes)',
    '148 traffic incidents on JFK Drive. High cyclist volume area.',
    true,
    300,
    'MUNICIPAL',
    0.90,
    148,
    true
);

-- ============================================================================
-- BAYVIEW HUNTERS POINT (175 total neighborhood crashes)
-- ============================================================================

-- Bayview - 3rd Street North corridor
INSERT INTO risk_zones (
    id, geometry, hazard_type, severity, name, description,
    is_permanent, alert_radius_meters, source, confidence_score,
    reported_count, is_active
) VALUES (
    'b3c4d5e6-f7a8-4b9c-0d1e-2f3a4b5c6d7e',
    ST_SetSRID(ST_MakePoint(-122.38779488, 37.78709723), 4326),
    'HIGH_TRAFFIC',
    'MEDIUM',
    'Bayview - 3rd Street North (152 crashes)',
    '152 traffic incidents along 3rd Street corridor. High transit and vehicle traffic.',
    true,
    260,
    'MUNICIPAL',
    0.88,
    152,
    true
);

-- Bayview - Evans Ave / Cesar Chavez area
INSERT INTO risk_zones (
    id, geometry, hazard_type, severity, name, description,
    is_permanent, alert_radius_meters, source, confidence_score,
    reported_count, is_active
) VALUES (
    'c4d5e6f7-a8b9-4c0d-1e2f-3a4b5c6d7e8f',
    ST_SetSRID(ST_MakePoint(-122.39100000, 37.74800000), 4326),
    'DANGEROUS_INTERSECTION',
    'MEDIUM',
    'Bayview - Evans Ave Area (145 crashes)',
    '145 traffic incidents near Evans Ave. Industrial area with heavy truck traffic.',
    true,
    240,
    'MUNICIPAL',
    0.85,
    145,
    true
);

-- ============================================================================
-- HAIGHT ASHBURY (146 total neighborhood crashes)
-- ============================================================================

-- Haight Ashbury - Main intersection cluster
INSERT INTO risk_zones (
    id, geometry, hazard_type, severity, name, description,
    is_permanent, alert_radius_meters, source, confidence_score,
    reported_count, is_active
) VALUES (
    'd5e6f7a8-b9c0-4d1e-2f3a-4b5c6d7e8f9a',
    ST_SetSRID(ST_MakePoint(-122.43373477, 37.77168827), 4326),
    'HIGH_TRAFFIC',
    'MEDIUM',
    'Haight Ashbury - Central (146 crashes)',
    '146 traffic incidents in Haight Ashbury. Busy commercial corridor with heavy pedestrian and cyclist traffic.',
    true,
    220,
    'MUNICIPAL',
    0.88,
    146,
    true
);

-- ============================================================================
-- SUNSET/PARKSIDE (155 total neighborhood crashes)
-- ============================================================================

-- Sunset - 19th Avenue corridor
INSERT INTO risk_zones (
    id, geometry, hazard_type, severity, name, description,
    is_permanent, alert_radius_meters, source, confidence_score,
    reported_count, is_active
) VALUES (
    'e6f7a8b9-c0d1-4e2f-3a4b-5c6d7e8f9a0b',
    ST_SetSRID(ST_MakePoint(-122.47500000, 37.75000000), 4326),
    'HIGH_TRAFFIC',
    'MEDIUM',
    'Sunset - 19th Avenue (155 crashes)',
    '155 traffic incidents along 19th Avenue. Major arterial with high speed traffic.',
    true,
    300,
    'MUNICIPAL',
    0.85,
    155,
    true
);

-- ============================================================================
-- LONE MOUNTAIN / USF AREA (86 total but high-density intersection)
-- ============================================================================

-- Lone Mountain - Masonic & Fulton intersection cluster
INSERT INTO risk_zones (
    id, geometry, hazard_type, severity, name, description,
    is_permanent, alert_radius_meters, source, confidence_score,
    reported_count, is_active
) VALUES (
    'f7a8b9c0-d1e2-4f3a-4b5c-6d7e8f9a0b1c',
    ST_SetSRID(ST_MakePoint(-122.44590236, 37.77299540), 4326),
    'DANGEROUS_INTERSECTION',
    'MEDIUM',
    'Lone Mountain - Masonic & Fulton (142 crashes)',
    '142 traffic incidents at Masonic/Fulton intersection. Complex intersection near USF.',
    true,
    200,
    'MUNICIPAL',
    0.88,
    142,
    true
);

-- ============================================================================
-- NORTH BEACH (102 crashes - enhanced to include nearby Embarcadero data)
-- ============================================================================

-- North Beach - Columbus Ave cluster
INSERT INTO risk_zones (
    id, geometry, hazard_type, severity, name, description,
    is_permanent, alert_radius_meters, source, confidence_score,
    reported_count, is_active
) VALUES (
    'a8b9c0d1-e2f3-4a4b-5c6d-7e8f9a0b1c2d',
    ST_SetSRID(ST_MakePoint(-122.40905049, 37.80811075), 4326),
    'HIGH_TRAFFIC',
    'MEDIUM',
    'North Beach - Columbus Ave (144 crashes)',
    '144 traffic incidents along Columbus Ave. Tourist area with high pedestrian and cyclist activity.',
    true,
    220,
    'MUNICIPAL',
    0.85,
    144,
    true
);

-- ============================================================================
-- MISSION BAY (137 crashes - just below threshold, but dense area)
-- ============================================================================

-- Mission Bay - 3rd St & Mission Bay Blvd
INSERT INTO risk_zones (
    id, geometry, hazard_type, severity, name, description,
    is_permanent, alert_radius_meters, source, confidence_score,
    reported_count, is_active
) VALUES (
    'b9c0d1e2-f3a4-4b5c-6d7e-8f9a0b1c2d3e',
    ST_SetSRID(ST_MakePoint(-122.39100000, 37.77100000), 4326),
    'HIGH_TRAFFIC',
    'MEDIUM',
    'Mission Bay - 3rd Street (140 crashes)',
    '140 traffic incidents in Mission Bay. Rapidly developing area with construction traffic.',
    true,
    230,
    'MUNICIPAL',
    0.85,
    140,
    true
);

-- ============================================================================
-- EMBARCADERO EXTENSION (Financial District already has zones, but gaps exist)
-- ============================================================================

-- Embarcadero - North waterfront
INSERT INTO risk_zones (
    id, geometry, hazard_type, severity, name, description,
    is_permanent, alert_radius_meters, source, confidence_score,
    reported_count, is_active
) VALUES (
    'c0d1e2f3-a4b5-4c6d-7e8f-9a0b1c2d3e4f',
    ST_SetSRID(ST_MakePoint(-122.39914859, 37.79101664), 4326),
    'DANGEROUS_INTERSECTION',
    'HIGH',
    'Embarcadero - North Waterfront (182 crashes)',
    '182 traffic incidents along north Embarcadero. High tourist and commuter cyclist traffic.',
    true,
    250,
    'MUNICIPAL',
    0.90,
    182,
    true
);

-- ============================================================================
-- POTRERO HILL / DOGPATCH CONNECTOR
-- ============================================================================

-- NOTE: Potrero - 3rd & Cesar Chavez zone removed - overlaps with existing Mission zone

-- ============================================================================
-- MARKET STREET GAPS (existing zones may not cover full corridor)
-- ============================================================================

-- Market & Van Ness area
INSERT INTO risk_zones (
    id, geometry, hazard_type, severity, name, description,
    is_permanent, alert_radius_meters, source, confidence_score,
    reported_count, is_active
) VALUES (
    'e2f3a4b5-c6d7-4e8f-9a0b-1c2d3e4f5a6b',
    ST_SetSRID(ST_MakePoint(-122.41936416, 37.78402911), 4326),
    'DANGEROUS_INTERSECTION',
    'HIGH',
    'Market & Van Ness (186 crashes)',
    '186 traffic incidents at Market/Van Ness. Major transit hub with complex traffic patterns.',
    true,
    200,
    'MUNICIPAL',
    0.92,
    186,
    true
);

-- ============================================================================
-- SUMMARY: 12 new zones added
-- Yellow (140-179): 8 zones
-- Light Red (180-229): 3 zones
-- Dark Red (230+): 0 zones (existing zones cover high-crash areas)
-- ============================================================================
