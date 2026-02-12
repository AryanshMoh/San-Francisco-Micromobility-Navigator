-- Remove the yellow risk zone at Potrero - 3rd & Cesar Chavez
-- This zone overlaps with the light red Mission zone nearby
-- Zone ID: d1e2f3a4-b5c6-4d7e-8f9a-0b1c2d3e4f5a
-- Location: 37.76578329, -122.40753422

-- Option 1: Deactivate the zone (keeps data but hides from display)
UPDATE risk_zones
SET is_active = false
WHERE id = 'd1e2f3a4-b5c6-4d7e-8f9a-0b1c2d3e4f5a';

-- Option 2: Delete the zone entirely (uncomment to use)
-- DELETE FROM risk_zones WHERE id = 'd1e2f3a4-b5c6-4d7e-8f9a-0b1c2d3e4f5a';
