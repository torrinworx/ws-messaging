import path from 'path';
import webpack from 'webpack';
import HtmlWebpackPlugin from 'html-webpack-plugin';
import { fileURLToPath } from 'url';
import dotenv from 'dotenv';

dotenv.config();
const { transformBabelAST } = await import("destam-dom/transform/htmlLiteral.js");
const __dirname = path.dirname(fileURLToPath(import.meta.url));
const env = process.env.NODE_ENV;

const config = {
    name: 'ws-messager', // Updated name to reflect the new project name
    target: 'web',
    stats: 'minimal',
    devtool: 'source-map',
    mode: env || 'development',
    entry: {
        ws_messager: './frontend/index.js', // Updated entry point name
    },
    output: {
        path: path.resolve(__dirname, 'build'),
        publicPath: '/',
        filename: 'index.js',
    },
    resolve: {
        extensions: ['.html', '.css', '.js', '.jsx'],
    },
    plugins: [
        new webpack.DefinePlugin({
            'process.env.HOST_URL': JSON.stringify(process.env.HOST_URL),
        }),
        new HtmlWebpackPlugin({
            template: './frontend/index.html',
        })
    ],
    module: {
        rules: [
            {
                test: /\.jsx?$/,
                exclude: /node_modules/,
                use: {
                    loader: 'babel-loader',
                    options: {
                        presets: ["@babel/preset-env", "@babel/preset-react"],
                        plugins: [
                            '@babel/plugin-syntax-jsx',
                            () => ({
                                visitor: {
                                    Program: path => {
                                        transformBabelAST(path.node);
                                    }
                                }
                            })
                        ],
                    }
                }
            },
            {
                test: /\.(png|jpg|jpeg|gif|ico|webp)$/,
                type: 'asset/resource',
                generator: {
                    filename: 'assets/[name][ext][query]',
                },
            },
            {
                test: /\.css$/,
                use: ['style-loader', 'css-loader'],
            },
        ]
    }
};

export default config;
