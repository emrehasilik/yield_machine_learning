import sql from 'mssql';
import dotenv from 'dotenv';
dotenv.config();

const config: sql.config = {
  server: process.env.DB_SERVER || 'DESKTOP-J0JOVUA',
  database: process.env.DB_NAME || 'wheat_yield_tr',
  user: process.env.DB_USER || 'wheat_user',
  password: process.env.DB_PASSWORD || 'Wheat2024!',
  options: {
    trustServerCertificate: true,
    enableArithAbort: true,
  },
};

let pool: sql.ConnectionPool | null = null;

export async function getPool(): Promise<sql.ConnectionPool> {
  if (!pool) {
    pool = await new sql.ConnectionPool(config).connect();
    console.log('SQL Server bağlantısı OK');
  }
  return pool;
}

export { sql };
