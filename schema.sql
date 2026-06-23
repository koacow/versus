-- VERSUS skeleton schema
-- Run:  mysql -u root -p versus < schema.sql
-- The four core tables for Phase I.
-- Students will extend with: predictions, votes, achievements,
-- user_achievements, follows, comments, plus triggers and a stored procedure.

DROP DATABASE IF EXISTS versus;
CREATE DATABASE versus;
USE versus;

CREATE TABLE Users (
    user_id       INT AUTO_INCREMENT PRIMARY KEY,
    username      VARCHAR(50)  NOT NULL UNIQUE,
    email         VARCHAR(255) NOT NULL UNIQUE,
    password      VARCHAR(255) NOT NULL,
    bio           TEXT,
    created_at    DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE Brackets (
    bracket_id           INT AUTO_INCREMENT PRIMARY KEY,
    host_id              INT NOT NULL,
    title                VARCHAR(255) NOT NULL,
    description          TEXT,
    entrant_count        INT NOT NULL,
    status               ENUM(
                             'draft',
                             'predictions_open',
                             'round_1','round_2','round_3','round_4','round_5',
                             'completed'
                         ) NOT NULL DEFAULT 'predictions_open',
    created_at           DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    prediction_deadline  DATETIME,
    CONSTRAINT chk_entrant_count CHECK (entrant_count IN (4,8,16,32)),
    CONSTRAINT fk_brackets_host  FOREIGN KEY (host_id) REFERENCES Users(user_id)
);

CREATE TABLE Entrants (
    entrant_id   INT AUTO_INCREMENT PRIMARY KEY,
    bracket_id   INT NOT NULL,
    seed         INT NOT NULL,
    name         VARCHAR(255) NOT NULL,
    img_url      VARCHAR(255),
    CONSTRAINT fk_entrants_bracket FOREIGN KEY (bracket_id) REFERENCES Brackets(bracket_id),
    CONSTRAINT uq_entrants_seed    UNIQUE (bracket_id, seed)
);

CREATE TABLE Matchups (
    matchup_id          INT AUTO_INCREMENT PRIMARY KEY,
    bracket_id          INT NOT NULL,
    round               INT NOT NULL,
    slot                INT NOT NULL,
    entrant_a_id        INT,
    entrant_b_id        INT,
    winner_entrant_id   INT,
    votes_a             INT NOT NULL DEFAULT 0,
    votes_b             INT NOT NULL DEFAULT 0,
    CONSTRAINT fk_matchups_bracket FOREIGN KEY (bracket_id)        REFERENCES Brackets(bracket_id),
    CONSTRAINT fk_matchups_a       FOREIGN KEY (entrant_a_id)      REFERENCES Entrants(entrant_id),
    CONSTRAINT fk_matchups_b       FOREIGN KEY (entrant_b_id)      REFERENCES Entrants(entrant_id),
    CONSTRAINT fk_matchups_winner  FOREIGN KEY (winner_entrant_id) REFERENCES Entrants(entrant_id),
    CONSTRAINT uq_matchups_slot    UNIQUE (bracket_id, round, slot)
);

CREATE TABLE Predictions (
    prediction_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id       INT NOT NULL,
    matchup_id    INT NOT NULL,
    predicted_winner_id INT NOT NULL,
    submitted_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    is_correct BOOLEAN,
    points_earned INT,
    CONSTRAINT fk_predictions_user FOREIGN KEY (user_id) REFERENCES Users(user_id),
    CONSTRAINT fk_predictions_matchup FOREIGN KEY (matchup_id) REFERENCES Matchups(matchup_id),
    CONSTRAINT fk_predictions_winner FOREIGN KEY (predicted_winner_id) REFERENCES Entrants(entrant_id),
    CONSTRAINT uq_predictions_user_matchup UNIQUE (user_id, matchup_id)
);

DELIMITER $$

CREATE TRIGGER prediction_open_check
BEFORE INSERT ON Predictions
FOR EACH ROW
BEGIN
    IF (
        SELECT status 
        FROM Brackets 
        WHERE bracket_id = (SELECT bracket_id FROM Matchups WHERE matchup_id = NEW.matchup_id)
        ) NOT IN ('predictions_open') THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Predictions are closed for this bracket';
    END IF;
END$$

CREATE TABLE Votes (
    vote_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    matchup_id INT NOT NULL,
    voted_for_entrant_id INT NOT NULL,
    CONSTRAINT fk_votes_user FOREIGN KEY (user_id) REFERENCES Users(user_id),
    CONSTRAINT fk_votes_matchup FOREIGN KEY (matchup_id) REFERENCES Matchups(matchup_id),
    CONSTRAINT fk_votes_entrant FOREIGN KEY (voted_for_entrant_id) REFERENCES Entrants(entrant_id),
    CONSTRAINT uq_votes_user_matchup UNIQUE (user_id, matchup_id)
);

CREATE TRIGGER vote_current_round_check
BEFORE INSERT ON Votes
FOR EACH ROW
BEGIN
    DECLARE current_round INT;
    SET current_round = (SELECT round FROM Matchups WHERE matchup_id = NEW.matchup_id);
    IF (SELECT status FROM Brackets WHERE bracket_id = (SELECT bracket_id FROM Matchups WHERE matchup_id = NEW.matchup_id)) NOT IN (CONCAT('round_', current_round)) THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Voting is not open for this matchup';
    END IF;
END$$

CREATE TABLE Achievements (
    achievement_code ENUM('bracket_maker', 'locked_in') PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT NOT NULL
);

CREATE TABLE User_Achievements (
    user_id INT NOT NULL,
    achievement_code ENUM('bracket_maker', 'locked_in') NOT NULL,
    achieved_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (user_id, achievement_code),
    CONSTRAINT fk_user_achievements_user FOREIGN KEY (user_id) REFERENCES Users(user_id),
    CONSTRAINT fk_user_achievements_achievement FOREIGN KEY (achievement_code) REFERENCES Achievements(achievement_code)
);

CREATE TRIGGER award_bracket_maker
AFTER INSERT ON Brackets
FOR EACH ROW
BEGIN
    DECLARE bracket_count INT;
    SELECT COUNT(*) INTO bracket_count FROM Brackets WHERE host_id = NEW.host_id;
    IF bracket_count = 1 THEN
        INSERT IGNORE INTO User_Achievements (user_id, achievement_code) VALUES (NEW.host_id, 'bracket_maker');
    END IF;
END$$

CREATE TRIGGER award_locked_in
AFTER INSERT ON Predictions
FOR EACH ROW
BEGIN
    DECLARE prediction_count INT;
    SELECT COUNT(*) INTO prediction_count FROM Predictions WHERE user_id = NEW.user_id;
    IF prediction_count = 10 THEN
        INSERT IGNORE INTO User_Achievements (user_id, achievement_code) VALUES (NEW.user_id, 'locked_in');
    END IF;
END$$

DELIMITER ;

CREATE TABLE Follows (
    follower_id INT NOT NULL,
    followed_id INT NOT NULL,
    followed_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (follower_id, followed_id),
    CONSTRAINT fk_follows_follower FOREIGN KEY (follower_id) REFERENCES Users(user_id),
    CONSTRAINT fk_follows_followed FOREIGN KEY (followed_id) REFERENCES Users(user_id),
    CONSTRAINT chk_no_self_follow CHECK (follower_id <> followed_id)
);

CREATE TABLE Comments (
    comment_id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    matchup_id INT NOT NULL,
    body TEXT NOT NULL,
    created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT fk_comments_user FOREIGN KEY (user_id) REFERENCES Users(user_id),
    CONSTRAINT fk_comments_matchup FOREIGN KEY (matchup_id) REFERENCES Matchups(matchup_id)
);

DELIMITER $$
-- Stored procedure: close a round, score predictions, promote winners, advance status
CREATE PROCEDURE close_round(IN p_bracket_id INT, IN p_round INT)
BEGIN
    DECLARE done         INT DEFAULT 0;
    DECLARE v_matchup_id INT;
    DECLARE v_winner_id  INT;
    DECLARE v_votes_a    INT;
    DECLARE v_votes_b    INT;
    DECLARE v_entrant_a  INT;
    DECLARE v_entrant_b  INT;
    DECLARE v_slot       INT;
    DECLARE v_next_slot  INT;
    DECLARE v_next_round INT;
    DECLARE v_total_rounds INT;
    DECLARE v_entrant_count INT;

    DECLARE cur CURSOR FOR
        SELECT matchup_id, slot, entrant_a_id, entrant_b_id, votes_a, votes_b
        FROM Matchups
        WHERE bracket_id = p_bracket_id AND round = p_round;
    DECLARE CONTINUE HANDLER FOR NOT FOUND SET done = 1;

    -- Determine total rounds from entrant_count
    SELECT entrant_count INTO v_entrant_count FROM Brackets WHERE bracket_id = p_bracket_id;
    SET v_total_rounds = CASE v_entrant_count
        WHEN 4  THEN 2
        WHEN 8  THEN 3
        WHEN 16 THEN 4
        WHEN 32 THEN 5
    END;

    START TRANSACTION;

    OPEN cur;
    round_loop: LOOP
        FETCH cur INTO v_matchup_id, v_slot, v_entrant_a, v_entrant_b, v_votes_a, v_votes_b;
        IF done THEN LEAVE round_loop; END IF;

        -- Pick winner: higher votes wins; ties go to entrant_a
        IF v_votes_b > v_votes_a THEN
            SET v_winner_id = v_entrant_b;
        ELSE
            SET v_winner_id = v_entrant_a;
        END IF;

        -- Set winner on this matchup
        UPDATE Matchups SET winner_entrant_id = v_winner_id WHERE matchup_id = v_matchup_id;

        -- Score predictions for this matchup
        UPDATE Predictions
        SET is_correct    = (predicted_winner_id = v_winner_id),
            points_earned = IF(predicted_winner_id = v_winner_id, 1, 0)
        WHERE matchup_id = v_matchup_id;

        -- Promote winner into next round's matchup slot
        IF p_round < v_total_rounds THEN
            SET v_next_round = p_round + 1;
            -- Slots pair up: slot 1&2 → slot 1, slot 3&4 → slot 2, etc.
            SET v_next_slot  = CEIL(v_slot / 2);
            IF v_slot % 2 = 1 THEN
                UPDATE Matchups
                SET entrant_a_id = v_winner_id
                WHERE bracket_id = p_bracket_id AND round = v_next_round AND slot = v_next_slot;
            ELSE
                UPDATE Matchups
                SET entrant_b_id = v_winner_id
                WHERE bracket_id = p_bracket_id AND round = v_next_round AND slot = v_next_slot;
            END IF;
        END IF;
    END LOOP;
    CLOSE cur;

    -- Advance bracket status
    IF p_round >= v_total_rounds THEN
        UPDATE Brackets SET status = 'completed' WHERE bracket_id = p_bracket_id;
    ELSE
        UPDATE Brackets
        SET status = CONCAT('round_', p_round + 1)
        WHERE bracket_id = p_bracket_id;
    END IF;

    COMMIT;
END$$