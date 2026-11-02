ALTER TABLE students
    ADD COLUMN IF NOT EXISTS library_id INTEGER REFERENCES libraries(id);
