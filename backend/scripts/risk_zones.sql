-- Risk zones generated from SF collision data (neighborhood bubbles)
-- Minimum 65 crashes, max 5 per neighborhood
-- Clear existing risk zones
DELETE FROM risk_zones;

-- Insert new risk zones
INSERT INTO risk_zones (
    id, geometry, hazard_type, severity, name, description,
    is_permanent, alert_radius_meters, source, confidence_score,
    reported_count, is_active
) VALUES (
    'd74c2d9f-bdf1-4d5e-be95-bfd31026f9e8',
    ST_SetSRID(ST_MakePoint(-122.40887695655805, 37.78105551175153), 4326),
    'HIGH_TRAFFIC',
    'HIGH',
    'South of Market (297 crashes)',
    '297 traffic incidents in South of Market. Fatal: 2, Injuries: 295',
    true,
    491,
    'MUNICIPAL',
    0.95,
    297,
    true
);
INSERT INTO risk_zones (
    id, geometry, hazard_type, severity, name, description,
    is_permanent, alert_radius_meters, source, confidence_score,
    reported_count, is_active
) VALUES (
    '09f6a589-6127-4214-aa5b-8f5f8423c256',
    ST_SetSRID(ST_MakePoint(-122.4148977124007, 37.783104267536906), 4326),
    'DANGEROUS_INTERSECTION',
    'HIGH',
    'Tenderloin (294 crashes)',
    '294 traffic incidents in Tenderloin. Fatal: 0, Injuries: 294',
    true,
    482,
    'MUNICIPAL',
    0.95,
    294,
    true
);
INSERT INTO risk_zones (
    id, geometry, hazard_type, severity, name, description,
    is_permanent, alert_radius_meters, source, confidence_score,
    reported_count, is_active
) VALUES (
    'de2f51e9-29f6-4b72-bdc4-9f746a21be95',
    ST_SetSRID(ST_MakePoint(-122.41947706596879, 37.78505566045907), 4326),
    'HIGH_TRAFFIC',
    'HIGH',
    'Tenderloin (260 crashes)',
    '260 traffic incidents in Tenderloin. Fatal: 5, Injuries: 255',
    true,
    385,
    'MUNICIPAL',
    0.95,
    260,
    true
);
INSERT INTO risk_zones (
    id, geometry, hazard_type, severity, name, description,
    is_permanent, alert_radius_meters, source, confidence_score,
    reported_count, is_active
) VALUES (
    '41adf1c9-eb5c-4dca-abd7-a9d7a75dc788',
    ST_SetSRID(ST_MakePoint(-122.40733588590267, 37.76537997910387), 4326),
    'HIGH_TRAFFIC',
    'HIGH',
    'Mission (241 crashes)',
    '241 traffic incidents in Mission. Fatal: 5, Injuries: 236',
    true,
    331,
    'MUNICIPAL',
    0.95,
    241,
    true
);
INSERT INTO risk_zones (
    id, geometry, hazard_type, severity, name, description,
    is_permanent, alert_radius_meters, source, confidence_score,
    reported_count, is_active
) VALUES (
    '83913afc-a3c6-4968-8591-9cb5a47621a7',
    ST_SetSRID(ST_MakePoint(-122.40302415830486, 37.787227409747615), 4326),
    'HIGH_TRAFFIC',
    'HIGH',
    'Financial District/South Beach (229 crashes)',
    '229 traffic incidents in Financial District/South Beach. Fatal: 2, Injuries: 227',
    true,
    297,
    'MUNICIPAL',
    0.95,
    229,
    true
);
INSERT INTO risk_zones (
    id, geometry, hazard_type, severity, name, description,
    is_permanent, alert_radius_meters, source, confidence_score,
    reported_count, is_active
) VALUES (
    '07fe343a-8094-4bdd-b530-38fcdad61a70',
    ST_SetSRID(ST_MakePoint(-122.4177144831102, 37.7692937719184), 4326),
    'DANGEROUS_INTERSECTION',
    'HIGH',
    'Mission (220 crashes)',
    '220 traffic incidents in Mission. Fatal: 0, Injuries: 220',
    true,
    271,
    'MUNICIPAL',
    0.95,
    220,
    true
);
INSERT INTO risk_zones (
    id, geometry, hazard_type, severity, name, description,
    is_permanent, alert_radius_meters, source, confidence_score,
    reported_count, is_active
) VALUES (
    'ebb911b4-b002-4901-ac22-86fa8912f9ea',
    ST_SetSRID(ST_MakePoint(-122.41700153685443, 37.784805562424005), 4326),
    'HIGH_TRAFFIC',
    'HIGH',
    'Tenderloin (210 crashes)',
    '210 traffic incidents in Tenderloin. Fatal: 2, Injuries: 208',
    true,
    242,
    'MUNICIPAL',
    0.95,
    210,
    true
);
INSERT INTO risk_zones (
    id, geometry, hazard_type, severity, name, description,
    is_permanent, alert_radius_meters, source, confidence_score,
    reported_count, is_active
) VALUES (
    'c5960a88-c34a-4036-a992-54788ffe2963',
    ST_SetSRID(ST_MakePoint(-122.41867284210406, 37.77300134247153), 4326),
    'DANGEROUS_INTERSECTION',
    'HIGH',
    'Mission (208 crashes)',
    '208 traffic incidents in Mission. Fatal: 0, Injuries: 208',
    true,
    237,
    'MUNICIPAL',
    0.95,
    208,
    true
);
INSERT INTO risk_zones (
    id, geometry, hazard_type, severity, name, description,
    is_permanent, alert_radius_meters, source, confidence_score,
    reported_count, is_active
) VALUES (
    'ba3db9f9-2cf6-433d-b9c0-32904d541e43',
    ST_SetSRID(ST_MakePoint(-122.42325724691503, 37.77171782469356), 4326),
    'HIGH_TRAFFIC',
    'HIGH',
    'Mission (208 crashes)',
    '208 traffic incidents in Mission. Fatal: 1, Injuries: 207',
    true,
    237,
    'MUNICIPAL',
    0.95,
    208,
    true
);
INSERT INTO risk_zones (
    id, geometry, hazard_type, severity, name, description,
    is_permanent, alert_radius_meters, source, confidence_score,
    reported_count, is_active
) VALUES (
    '4118e9ad-872c-4c13-84d9-837298091291',
    ST_SetSRID(ST_MakePoint(-122.4231210531655, 37.77310144151465), 4326),
    'HIGH_TRAFFIC',
    'HIGH',
    'Hayes Valley (207 crashes)',
    '207 traffic incidents in Hayes Valley. Fatal: 3, Injuries: 204',
    true,
    234,
    'MUNICIPAL',
    0.95,
    207,
    true
);
INSERT INTO risk_zones (
    id, geometry, hazard_type, severity, name, description,
    is_permanent, alert_radius_meters, source, confidence_score,
    reported_count, is_active
) VALUES (
    'aff44695-ed8a-4b96-9dd3-41d0a10a3333',
    ST_SetSRID(ST_MakePoint(-122.42297028317269, 37.78107478855329), 4326),
    'DANGEROUS_INTERSECTION',
    'HIGH',
    'Western Addition (207 crashes)',
    '207 traffic incidents in Western Addition. Fatal: 0, Injuries: 207',
    true,
    234,
    'MUNICIPAL',
    0.95,
    207,
    true
);
INSERT INTO risk_zones (
    id, geometry, hazard_type, severity, name, description,
    is_permanent, alert_radius_meters, source, confidence_score,
    reported_count, is_active
) VALUES (
    'b3272ee2-0eb9-43ff-80ff-94044f567c50',
    ST_SetSRID(ST_MakePoint(-122.41892612422124, 37.786567508907844), 4326),
    'HIGH_TRAFFIC',
    'HIGH',
    'Tenderloin (204 crashes)',
    '204 traffic incidents in Tenderloin. Fatal: 1, Injuries: 203',
    true,
    225,
    'MUNICIPAL',
    0.95,
    204,
    true
);
INSERT INTO risk_zones (
    id, geometry, hazard_type, severity, name, description,
    is_permanent, alert_radius_meters, source, confidence_score,
    reported_count, is_active
) VALUES (
    '606178ac-05db-41c0-b858-165963cbbe2d',
    ST_SetSRID(ST_MakePoint(-122.42245663918825, 37.769222323502284), 4326),
    'HIGH_TRAFFIC',
    'HIGH',
    'Mission (203 crashes)',
    '203 traffic incidents in Mission. Fatal: 1, Injuries: 202',
    true,
    222,
    'MUNICIPAL',
    0.95,
    203,
    true
);
INSERT INTO risk_zones (
    id, geometry, hazard_type, severity, name, description,
    is_permanent, alert_radius_meters, source, confidence_score,
    reported_count, is_active
) VALUES (
    '794ba6ca-0dd6-4e88-b295-c4b3d641e925',
    ST_SetSRID(ST_MakePoint(-122.40281063347362, 37.7890019027898), 4326),
    'DANGEROUS_INTERSECTION',
    'HIGH',
    'Financial District/South Beach (200 crashes)',
    '200 traffic incidents in Financial District/South Beach. Fatal: 0, Injuries: 200',
    true,
    214,
    'MUNICIPAL',
    0.95,
    200,
    true
);
INSERT INTO risk_zones (
    id, geometry, hazard_type, severity, name, description,
    is_permanent, alert_radius_meters, source, confidence_score,
    reported_count, is_active
) VALUES (
    '47354e1d-e3f9-49bf-a19e-e0d691e452e0',
    ST_SetSRID(ST_MakePoint(-122.41255247698095, 37.78293336036249), 4326),
    'HIGH_TRAFFIC',
    'MEDIUM',
    'Tenderloin (198 crashes)',
    '198 traffic incidents in Tenderloin. Fatal: 1, Injuries: 197',
    true,
    208,
    'MUNICIPAL',
    0.95,
    198,
    true
);
INSERT INTO risk_zones (
    id, geometry, hazard_type, severity, name, description,
    is_permanent, alert_radius_meters, source, confidence_score,
    reported_count, is_active
) VALUES (
    '7168f849-32a3-4c76-991f-c966afb8e851',
    ST_SetSRID(ST_MakePoint(-122.43084245596951, 37.77927888423194), 4326),
    'HIGH_TRAFFIC',
    'MEDIUM',
    'Western Addition (193 crashes)',
    '193 traffic incidents in Western Addition. Fatal: 2, Injuries: 191',
    true,
    194,
    'MUNICIPAL',
    0.95,
    193,
    true
);
INSERT INTO risk_zones (
    id, geometry, hazard_type, severity, name, description,
    is_permanent, alert_radius_meters, source, confidence_score,
    reported_count, is_active
) VALUES (
    '9f4754e9-eb29-4793-a163-d59928f69e41',
    ST_SetSRID(ST_MakePoint(-122.41291233598314, 37.77722917744369), 4326),
    'HIGH_TRAFFIC',
    'MEDIUM',
    'South of Market (189 crashes)',
    '189 traffic incidents in South of Market. Fatal: 1, Injuries: 188',
    true,
    182,
    'MUNICIPAL',
    0.95,
    189,
    true
);
INSERT INTO risk_zones (
    id, geometry, hazard_type, severity, name, description,
    is_permanent, alert_radius_meters, source, confidence_score,
    reported_count, is_active
) VALUES (
    '0bf9426e-56f7-4739-a535-972f81e29efa',
    ST_SetSRID(ST_MakePoint(-122.42458892773983, 37.77492886662397), 4326),
    'HIGH_TRAFFIC',
    'MEDIUM',
    'Hayes Valley (188 crashes)',
    '188 traffic incidents in Hayes Valley. Fatal: 2, Injuries: 186',
    true,
    180,
    'MUNICIPAL',
    0.95,
    188,
    true
);
INSERT INTO risk_zones (
    id, geometry, hazard_type, severity, name, description,
    is_permanent, alert_radius_meters, source, confidence_score,
    reported_count, is_active
) VALUES (
    'a8fcabe5-abda-4063-8b7b-ee6ccf59c54b',
    ST_SetSRID(ST_MakePoint(-122.42084360191593, 37.78901588187292), 4326),
    'HIGH_TRAFFIC',
    'MEDIUM',
    'Nob Hill (188 crashes)',
    '188 traffic incidents in Nob Hill. Fatal: 2, Injuries: 186',
    true,
    180,
    'MUNICIPAL',
    0.95,
    188,
    true
);
INSERT INTO risk_zones (
    id, geometry, hazard_type, severity, name, description,
    is_permanent, alert_radius_meters, source, confidence_score,
    reported_count, is_active
) VALUES (
    'a7fff0be-b36c-49a3-a036-4e618ce9d388',
    ST_SetSRID(ST_MakePoint(-122.41519594018204, 37.774967648191556), 4326),
    'HIGH_TRAFFIC',
    'MEDIUM',
    'South of Market (168 crashes)',
    '168 traffic incidents in South of Market. Fatal: 1, Injuries: 167',
    true,
    122,
    'MUNICIPAL',
    0.95,
    168,
    true
);
INSERT INTO risk_zones (
    id, geometry, hazard_type, severity, name, description,
    is_permanent, alert_radius_meters, source, confidence_score,
    reported_count, is_active
) VALUES (
    'a109abd8-444a-497a-8476-9445edb3ae4e',
    ST_SetSRID(ST_MakePoint(-122.42895354400332, 37.7672724377402), 4326),
    'DANGEROUS_INTERSECTION',
    'MEDIUM',
    'Castro/Upper Market (166 crashes)',
    '166 traffic incidents in Castro/Upper Market. Fatal: 0, Injuries: 166',
    true,
    117,
    'MUNICIPAL',
    0.95,
    166,
    true
);