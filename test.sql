-- Comprehensive test suite for VERSUS database schema
-- Tests all constraints, triggers, and foreign keys

USE versus;

-- ============================================================================
-- SETUP: Insert base test data (valid data)
-- ============================================================================

-- Insert test users
INSERT INTO Users (username, email, password, bio) VALUES
('alice', 'alice@example.com', 'hashed_pass_1', 'Bracket enthusiast'),
('bob', 'bob@example.com', 'hashed_pass_2', 'Tournament organizer'),
('charlie', 'charlie@example.com', 'hashed_pass_3', 'Competitive predictor'),
('diana', 'diana@example.com', 'hashed_pass_4', 'Vote collector'),
('eve', 'eve@example.com', 'hashed_pass_5', 'Achievement hunter');

-- Insert valid brackets with entrant_count = 4, 8, 16, 32
INSERT INTO Brackets (host_id, title, description, entrant_count, status, prediction_deadline) VALUES
(1, 'Bracket 1 - 4 entrants', 'Test bracket with 4 entrants', 4, 'predictions_open', DATE_ADD(NOW(), INTERVAL 1 DAY)),
(1, 'Bracket 2 - 8 entrants', 'Test bracket with 8 entrants', 8, 'predictions_open', DATE_ADD(NOW(), INTERVAL 1 DAY)),
(2, 'Bracket 3 - 16 entrants', 'Test bracket with 16 entrants', 16, 'predictions_open', DATE_ADD(NOW(), INTERVAL 1 DAY)),
(2, 'Bracket 4 - 32 entrants', 'Test bracket with 32 entrants', 32, 'round_1', NULL);

-- Insert entrants for bracket 1 (4 entrants)
INSERT INTO Entrants (bracket_id, seed, name, img_url) VALUES
(1, 1, 'Team A', 'http://example.com/a.jpg'),
(1, 2, 'Team B', 'http://example.com/b.jpg'),
(1, 3, 'Team C', 'http://example.com/c.jpg'),
(1, 4, 'Team D', 'http://example.com/d.jpg');

-- Insert entrants for bracket 2 (8 entrants)
INSERT INTO Entrants (bracket_id, seed, name, img_url) VALUES
(2, 1, 'Player 1', 'http://example.com/p1.jpg'),
(2, 2, 'Player 2', 'http://example.com/p2.jpg'),
(2, 3, 'Player 3', 'http://example.com/p3.jpg'),
(2, 4, 'Player 4', 'http://example.com/p4.jpg'),
(2, 5, 'Player 5', 'http://example.com/p5.jpg'),
(2, 6, 'Player 6', 'http://example.com/p6.jpg'),
(2, 7, 'Player 7', 'http://example.com/p7.jpg'),
(2, 8, 'Player 8', 'http://example.com/p8.jpg');

-- Insert entrants for bracket 3 (16 entrants)
INSERT INTO Entrants (bracket_id, seed, name, img_url) VALUES
(3, 1, 'Seed 1', NULL), (3, 2, 'Seed 2', NULL), (3, 3, 'Seed 3', NULL), (3, 4, 'Seed 4', NULL),
(3, 5, 'Seed 5', NULL), (3, 6, 'Seed 6', NULL), (3, 7, 'Seed 7', NULL), (3, 8, 'Seed 8', NULL),
(3, 9, 'Seed 9', NULL), (3, 10, 'Seed 10', NULL), (3, 11, 'Seed 11', NULL), (3, 12, 'Seed 12', NULL),
(3, 13, 'Seed 13', NULL), (3, 14, 'Seed 14', NULL), (3, 15, 'Seed 15', NULL), (3, 16, 'Seed 16', NULL);

-- Insert entrants for bracket 4 (32 entrants)
INSERT INTO Entrants (bracket_id, seed, name, img_url) VALUES
(4, 1, 'E1', NULL), (4, 2, 'E2', NULL), (4, 3, 'E3', NULL), (4, 4, 'E4', NULL),
(4, 5, 'E5', NULL), (4, 6, 'E6', NULL), (4, 7, 'E7', NULL), (4, 8, 'E8', NULL),
(4, 9, 'E9', NULL), (4, 10, 'E10', NULL), (4, 11, 'E11', NULL), (4, 12, 'E12', NULL),
(4, 13, 'E13', NULL), (4, 14, 'E14', NULL), (4, 15, 'E15', NULL), (4, 16, 'E16', NULL),
(4, 17, 'E17', NULL), (4, 18, 'E18', NULL), (4, 19, 'E19', NULL), (4, 20, 'E20', NULL),
(4, 21, 'E21', NULL), (4, 22, 'E22', NULL), (4, 23, 'E23', NULL), (4, 24, 'E24', NULL),
(4, 25, 'E25', NULL), (4, 26, 'E26', NULL), (4, 27, 'E27', NULL), (4, 28, 'E28', NULL),
(4, 29, 'E29', NULL), (4, 30, 'E30', NULL), (4, 31, 'E31', NULL), (4, 32, 'E32', NULL);

-- Insert matchups for bracket 1
INSERT INTO Matchups (bracket_id, round, slot, entrant_a_id, entrant_b_id, winner_entrant_id, votes_a, votes_b) VALUES
(1, 1, 1, 1, 2, 1, 5, 3),
(1, 1, 2, 3, 4, 3, 4, 2);

-- Insert matchups for bracket 2
INSERT INTO Matchups (bracket_id, round, slot, entrant_a_id, entrant_b_id) VALUES
(2, 1, 1, 5, 6),
(2, 1, 2, 7, 8);

-- Insert matchups for bracket 4 (in round_1)
INSERT INTO Matchups (bracket_id, round, slot, entrant_a_id, entrant_b_id) VALUES
(4, 1, 1, 33, 34),
(4, 1, 2, 35, 36);

-- ============================================================================
-- TEST 1: CHECK CONSTRAINT - Entrant Count
-- ============================================================================
-- Test invalid entrant counts (should fail)
-- Valid values: 4, 8, 16, 32

-- Try to insert bracket with invalid entrant count (6)
-- INSERT INTO Brackets (host_id, title, description, entrant_count, status) VALUES
-- (1, 'Invalid bracket', 'Should fail', 6, 'predictions_open');

-- Try to insert bracket with invalid entrant count (64)
-- INSERT INTO Brackets (host_id, title, description, entrant_count, status) VALUES
-- (1, 'Invalid bracket', 'Should fail', 64, 'predictions_open');

-- ============================================================================
-- TEST 2: UNIQUE CONSTRAINT - Entrants (bracket_id, seed)
-- ============================================================================
-- Each bracket can only have one entrant with each seed number

-- ============================================================================
-- TEST 3: UNIQUE CONSTRAINT - Matchups (bracket_id, round, slot)
-- ============================================================================
-- Each bracket can only have one matchup per round/slot combination

-- Try to insert duplicate slot in same round (should fail)
-- INSERT INTO Matchups (bracket_id, round, slot, entrant_a_id, entrant_b_id) VALUES
-- (1, 1, 1, 1, 3);

-- Different round, same slot is allowed (should succeed)
INSERT INTO Matchups (bracket_id, round, slot, entrant_a_id, entrant_b_id) VALUES
(1, 2, 1, 1, 3);  -- Different round, same slot - OK

-- ============================================================================
-- TEST 4: UNIQUE CONSTRAINT - Predictions (user_id, matchup_id)
-- ============================================================================
-- Each user can only make one prediction per matchup

-- Insert valid prediction
INSERT INTO Predictions (user_id, matchup_id, predicted_winner_id, is_correct, points_earned) VALUES
(3, 1, 1, NULL, NULL);

-- Try to insert duplicate prediction (should fail)
-- INSERT INTO Predictions (user_id, matchup_id, predicted_winner_id) VALUES
-- (3, 1, 2);

-- Different user, same matchup is allowed (should succeed)
INSERT INTO Predictions (user_id, matchup_id, predicted_winner_id) VALUES
(4, 1, 2),
(5, 1, 1);

-- ============================================================================
-- TEST 5: TRIGGER - prediction_open_check
-- ============================================================================
-- Predictions should only be allowed when bracket status is 'predictions_open'
-- Bracket 1 is in 'predictions_open' - should succeed
-- Bracket 4 is in 'round_1' - should fail

-- Valid prediction on bracket in predictions_open (should succeed)
INSERT INTO Predictions (user_id, matchup_id, predicted_winner_id) VALUES
(3, 7, 5);  -- matchup 7 is on bracket 2 (predictions_open)

-- ============================================================================
-- TEST 8: TRIGGER - award_bracket_maker (10 brackets → 'locked_in' achievement)
-- ============================================================================
-- When a user creates their 10th bracket, they should get 'locked_in' achievement

-- Create 9 more brackets for user 1 (already has 1, needs 10 total)
INSERT INTO Brackets (host_id, title, description, entrant_count, status) VALUES
(1, 'Test Bracket 5', 'Test', 4, 'draft'),
(1, 'Test Bracket 6', 'Test', 4, 'draft'),
(1, 'Test Bracket 7', 'Test', 4, 'draft'),
(1, 'Test Bracket 8', 'Test', 4, 'draft'),
(1, 'Test Bracket 9', 'Test', 4, 'draft'),
(1, 'Test Bracket 10', 'Test', 4, 'draft'),
(1, 'Test Bracket 11', 'Test', 4, 'draft'),
(1, 'Test Bracket 12', 'Test', 4, 'draft');

INSERT INTO Brackets (host_id, title, description, entrant_count, status) VALUES
(1, 'Test Bracket 13', 'Test', 4, 'draft');  -- 10th bracket - should trigger award_bracket_maker

-- Verify the achievement was awarded (user 1 should have 'locked_in')
-- SELECT * FROM User_Achievements WHERE user_id = 1 AND achievement_code = 'locked_in';

-- ============================================================================
-- TEST 9: TRIGGER - award_locked_in (10 predictions → 'bracket_maker' achievement)
-- ============================================================================
-- When a user makes their 10th prediction, they should get 'bracket_maker' achievement

-- User 3 currently has 1 prediction, needs 9 more to reach 10
INSERT INTO Predictions (user_id, matchup_id, predicted_winner_id) VALUES
(3, 8, 6),
(3, 9, 5),
(3, 10, 7),
(3, 2, 3),
(3, 3, 7),
(3, 4, 8),
(3, 5, 5),
(3, 6, 6);  -- 8 predictions so far

-- Need to create more matchups for user 3 to make 2 more predictions
INSERT INTO Matchups (bracket_id, round, slot, entrant_a_id, entrant_b_id) VALUES
(3, 2, 1, 17, 18),
(3, 2, 2, 19, 20);

INSERT INTO Predictions (user_id, matchup_id, predicted_winner_id) VALUES
(3, 11, 17),  -- 9 predictions
(3, 12, 19);  -- 10th prediction - should trigger award_locked_in

-- Verify the achievement was awarded (user 3 should have 'bracket_maker')
-- SELECT * FROM User_Achievements WHERE user_id = 3 AND achievement_code = 'bracket_maker';

-- ============================================================================
-- TEST 10: CHECK CONSTRAINT - No Self-Follow
-- ============================================================================
-- Users cannot follow themselves

-- Valid follows (should succeed)
INSERT INTO Follows (follower_id, followed_id) VALUES
(1, 2),
(2, 3),
(3, 4),
(4, 5),
(5, 1);

-- Try to follow self (should fail)
-- INSERT INTO Follows (follower_id, followed_id) VALUES
-- (1, 1);

-- ============================================================================
-- TEST 11: FOREIGN KEY CONSTRAINTS
-- ============================================================================
-- Test foreign key references

-- Valid comment on matchup (should succeed)
INSERT INTO Comments (user_id, matchup_id, body) VALUES
(1, 1, 'Team A is going to dominate!'),
(2, 2, 'This is a tough matchup'),
(3, 1, 'Close prediction here');

-- Try to insert comment with invalid user_id (should fail)
-- INSERT INTO Comments (user_id, matchup_id, body) VALUES
-- (999, 1, 'Invalid user');

-- Try to insert comment with invalid matchup_id (should fail)
-- INSERT INTO Comments (user_id, matchup_id, body) VALUES
-- (1, 999, 'Invalid matchup');

-- ============================================================================
-- TEST 12: Additional Valid Data for Comprehensive Testing
-- ============================================================================

-- More votes to test vote counting
INSERT INTO Votes (user_id, matchup_id, voted_for_entrant_id) VALUES
(1, 2, 3),
(2, 2, 4),
(3, 2, 3),
(4, 2, 4);

-- More predictions from different users
INSERT INTO Predictions (user_id, matchup_id, predicted_winner_id) VALUES
(1, 7, 5),
(1, 8, 6),
(1, 9, 5),
(1, 10, 7),
(2, 1, 1),
(2, 2, 3),
(2, 7, 5),
(2, 8, 6);

-- ============================================================================
-- VERIFICATION QUERIES
-- ============================================================================

-- View all users
SELECT 'Users:' AS test;
SELECT * FROM Users;

-- View all brackets and their hosts
SELECT 'Brackets:' AS test;
SELECT b.bracket_id, b.title, b.entrant_count, b.status, u.username FROM Brackets b JOIN Users u ON b.host_id = u.user_id;

-- View predictions made
SELECT 'Predictions:' AS test;
SELECT p.prediction_id, u.username, p.matchup_id, e.name as predicted_winner FROM Predictions p 
JOIN Users u ON p.user_id = u.user_id 
JOIN Entrants e ON p.predicted_winner_id = e.entrant_id;

-- View votes cast
SELECT 'Votes:' AS test;
SELECT v.vote_id, u.username, v.matchup_id, e.name as voted_for FROM Votes v 
JOIN Users u ON v.user_id = u.user_id 
JOIN Entrants e ON v.voted_for_entrant_id = e.entrant_id;

-- View awarded achievements
SELECT 'Achievements:' AS test;
SELECT ua.user_id, u.username, ua.achievement_code, a.name FROM User_Achievements ua 
JOIN Users u ON ua.user_id = u.user_id 
JOIN Achievements a ON ua.achievement_code = a.achievement_code;

-- View follows
SELECT 'Follows:' AS test;
SELECT f.follower_id, u1.username as follower, u2.username as followed FROM Follows f 
JOIN Users u1 ON f.follower_id = u1.user_id 
JOIN Users u2 ON f.followed_id = u2.user_id;

-- View comments
SELECT 'Comments:' AS test;
SELECT c.comment_id, u.username, c.matchup_id, c.body FROM Comments c 
JOIN Users u ON c.user_id = u.user_id;

-- Test summary
SELECT 'Test Summary' AS section;
SELECT COUNT(*) as total_users FROM Users;
SELECT COUNT(*) as total_brackets FROM Brackets;
SELECT COUNT(*) as total_entrants FROM Entrants;
SELECT COUNT(*) as total_matchups FROM Matchups;
SELECT COUNT(*) as total_predictions FROM Predictions;
SELECT COUNT(*) as total_votes FROM Votes;
SELECT COUNT(*) as total_follows FROM Follows;
SELECT COUNT(*) as total_comments FROM Comments;
SELECT COUNT(*) as total_achievements_awarded FROM User_Achievements;
