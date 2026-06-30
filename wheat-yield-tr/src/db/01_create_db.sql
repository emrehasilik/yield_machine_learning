-- ============================================================
-- BUGDAY VERIM TAHMINI — VERITABANI OLUSTURMA (SQL Server)
-- SSMS'de once "master" veritabanina baglan, sonra bu komutu calistir
-- ============================================================

IF NOT EXISTS (SELECT name FROM sys.databases WHERE name = 'wheat_yield_tr')
BEGIN
    CREATE DATABASE wheat_yield_tr
        COLLATE Turkish_CI_AS;
END
GO
